"""Small, strict helpers for untrusted model responses."""
import math


def text(value, default=""):
    return value.strip() if isinstance(value, str) and value.strip() else default


def strings(value):
    return [s.strip() for s in value if isinstance(s, str) and s.strip()] if isinstance(value, list) else []


def number(value, low, high):
    if isinstance(value, bool):
        raise ValueError("Invalid numeric field")
    result = float(value)
    if not math.isfinite(result) or not low <= result <= high:
        raise ValueError("Score outside allowed range")
    return round(result)
