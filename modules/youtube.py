"""Optional, bounded learning-video lookups with visible failures."""
from concurrent.futures import ThreadPoolExecutor
import requests
from modules import config
from modules.validation import text

_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


class VideoError(Exception):
    pass


def _lookup(skill, practice=False):
    try:
        response = requests.get(_SEARCH_URL, params={
            "part": "snippet", "q": f"{skill} hands on practice exercises project tutorial" if practice else f"learn {skill} tutorial for beginners",
            "type": "video", "maxResults": 1, "relevanceLanguage": "en",
            "safeSearch": "strict", "key": config.YOUTUBE_API_KEY,
        }, timeout=12)
        data = response.json()
        if response.status_code >= 400 or not isinstance(data, dict) or data.get("error"):
            raise VideoError("Learning videos unavailable. Check YouTube key/quota or retry later.")
        items = data.get("items")
        if not isinstance(items, list):
            raise VideoError("Video service returned an invalid response.")
        if not items:
            return None
        item = items[0]
        video_id = item["id"]["videoId"]
        snippet = item["snippet"]
        if not isinstance(video_id, str) or not video_id:
            raise ValueError()
        return {"skill": skill, "title": text(snippet.get("title"), f"Learn {skill}"),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "channel": text(snippet.get("channelTitle")), "thumbnail": ""}
    except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError) as exc:
        # Do not surface exception URLs: they may contain the API key.
        raise VideoError("Could not load learning videos. Check your connection and retry.") from exc


def get_learning_videos(skills, max_skills=6, practice=False):
    if not config.youtube_enabled() or not skills:
        return []
    selected = list(dict.fromkeys(skills))[:max_skills]
    with ThreadPoolExecutor(max_workers=min(3, len(selected))) as pool:
        return [video for video in pool.map(lambda skill: _lookup(skill, practice=practice), selected) if video]
