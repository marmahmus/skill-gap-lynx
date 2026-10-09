"""Thin, dependency-light Groq client.

Uses the OpenAI-compatible REST endpoints via ``requests`` so behaviour is
fully predictable and independent of any SDK version. Handles chat
completions (JSON mode) and Whisper audio transcription.
"""
import json
import re
import time

import requests

from modules import config

_MAX_RETRIES = 2  # extra attempts on transient rate-limit (429) responses


class GroqError(Exception):
    """Raised when the Groq API returns an error or an unusable response."""


def _extract_json(text):
    """Best-effort parse of a JSON object from a model response.

    Reasoning models occasionally wrap JSON in prose or code fences, so we
    fall back to grabbing the outermost ``{...}`` block.
    """
    if not isinstance(text, str):
        raise GroqError("AI response did not contain text. Please retry.")
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip ```json ... ``` fences if present.
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass

    # Fall back to the first balanced-looking object.
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise GroqError("Model did not return valid JSON.")


def _safe_response_json(resp):
    """`.json()` raises a raw ValueError/JSONDecodeError, not a GroqError,
    if the server ever returns a non-JSON body (e.g. a gateway timeout
    page during an outage). Convert it into a GroqError with enough
    context (status code and a text snippet) to debug it."""
    try:
        data = resp.json()
    except ValueError as exc:
        raise GroqError(f"AI service returned an unreadable response (HTTP {resp.status_code}). Please retry.") from exc
    if not isinstance(data, dict):
        raise GroqError("AI service returned an unexpected response. Please retry.")
    if resp.status_code >= 400 or data.get("error"):
        labels = {401: "Invalid Groq API key.", 403: "Groq access denied.", 429: "Rate limit reached. Please wait and retry."}
        raise GroqError(labels.get(resp.status_code, f"AI service request failed (HTTP {resp.status_code}). Please retry."))
    return data


def chat_json(messages, temperature=0.3, max_tokens=2500):
    """Call the chat completion endpoint in JSON mode and return a dict."""
    if not config.GROQ_API_KEY:
        raise GroqError("GROQ_API_KEY is not set. Add it to your .env file.")

    url = f"{config.GROQ_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }

    data = _post_with_retry(url, headers, payload)
    if isinstance(data, dict) and data.get("error"):
        raise GroqError(data["error"].get("message", "Unknown Groq error."))

    try:
        choice = data["choices"][0]
        content = choice["message"]["content"]
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise GroqError("Unexpected response shape from Groq.") from exc

    # If the response was cut off mid-JSON because max_tokens ran out,
    # retry once with a bigger budget before giving up.
    if not isinstance(choice, dict):
        raise GroqError("Unexpected response shape from Groq.")
    if choice.get("finish_reason") == "length":
        bigger_budget = min(max_tokens * 2, 8000)
        if bigger_budget > max_tokens:
            payload["max_tokens"] = bigger_budget
            data = _post_with_retry(url, headers, payload)
            if isinstance(data, dict) and data.get("error"):
                raise GroqError(data["error"].get("message", "Unknown Groq error."))
            try:
                choice = data["choices"][0]
                content = choice["message"]["content"]
            except (KeyError, IndexError, TypeError, AttributeError) as exc:
                raise GroqError("Unexpected response shape from Groq.") from exc
            if choice.get("finish_reason") == "length":
                raise GroqError(
                    "The model's response was cut off (too long) even after "
                    "retrying with a larger token budget. Try a shorter CV/JD."
                )

    parsed = _extract_json(content)
    # _extract_json() only guarantees valid JSON, not that it's an object.
    # Every caller expects a dict, so this check is centralised here.
    if not isinstance(parsed, dict):
        raise GroqError("Model returned valid JSON but not the expected object shape.")
    return parsed


def _post_with_retry(url, headers, payload):
    """POST JSON, retrying briefly on 429 rate-limit responses."""
    last_error = "Request failed."
    for attempt in range(_MAX_RETRIES + 1):
        try:
            resp = requests.post(
                url, headers=headers, json=payload, timeout=config.REQUEST_TIMEOUT
            )
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            if attempt < _MAX_RETRIES:
                time.sleep(1 + attempt)
                continue
            raise GroqError("Could not contact the AI service. Check your connection and retry.") from exc

        except requests.exceptions.RequestException as exc:
            raise GroqError("AI request failed. Please retry.") from exc

        if resp.status_code in (429, 500, 502, 503, 504) and attempt < _MAX_RETRIES:
            wait = _retry_after(resp)
            last_error = "Rate limit reached."
            time.sleep(wait)
            continue
        return _safe_response_json(resp)

    raise GroqError(last_error)


def _retry_after(resp):
    """Seconds to wait before retrying, from the Retry-After header (capped)."""
    try:
        return min(8.0, max(1.0, float(resp.headers.get("retry-after", 2))))
    except (TypeError, ValueError):
        return 2.0


def transcribe(audio_bytes, filename="answer.wav", language="English"):
    """Transcribe raw audio bytes to text using Groq Whisper."""
    if not config.GROQ_API_KEY:
        raise GroqError("GROQ_API_KEY is not set. Add it to your .env file.")
    if not audio_bytes:
        raise GroqError("No audio was captured.")

    url = f"{config.GROQ_BASE_URL}/audio/transcriptions"
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}"}
    ext = filename.rsplit(".", 1)[-1].lower()
    mime = {
        "wav": "audio/wav", "webm": "audio/webm", "mp3": "audio/mpeg",
        "m4a": "audio/mp4", "ogg": "audio/ogg", "flac": "audio/flac",
    }.get(ext, "application/octet-stream")
    files = {"file": (filename, audio_bytes, mime)}
    data = {"model": config.WHISPER_MODEL, "response_format": "json",
            "language": "ur" if language == "Urdu" else "en"}
    if language == "Urdu":
        data["prompt"] = "یہ اردو انٹرویو کا جواب ہے۔ اسے اردو رسم الخط میں لکھیں۔"

    try:
        resp = requests.post(
            url,
            headers=headers,
            files=files,
            data=data,
            timeout=config.REQUEST_TIMEOUT,
        )
    except requests.exceptions.RequestException as exc:
        raise GroqError("Could not transcribe audio. Check your connection and record again.") from exc

    payload = _safe_response_json(resp)
    if isinstance(payload, dict) and payload.get("error"):
        raise GroqError(payload["error"].get("message", "Transcription failed."))

    value = payload.get("text")
    if not isinstance(value, str) or not value.strip():
        raise GroqError("No speech detected. Record again or type your answer.")
    if language == "Urdu" and any("\u0900" <= char <= "\u097f" for char in value):
        raise GroqError("Urdu transcription returned an incorrect script. Please record again or type your answer in Urdu.")
    return value.strip()
