"""Small YouTube Data API client using only the Python standard library."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

API_ROOT = "https://www.googleapis.com/youtube/v3"
MAX_RESULTS = 25
HTTP_TIMEOUT_SECONDS = 8


class YouTubeError(Exception):
    def __init__(self, code: str, message: str, status: int = 502) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def search_videos(
    topic: str,
    days: int,
    api_key: str,
    *,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Use exactly search.list and videos.list to return real video snapshots."""

    current_time = now or datetime.now(timezone.utc)
    published_after = current_time - timedelta(days=days)
    search_data = _request(
        "search",
        {
            "part": "snippet",
            "type": "video",
            "q": topic,
            "publishedAfter": published_after.isoformat().replace("+00:00", "Z"),
            "videoDuration": "short",
            "order": "relevance",
            "maxResults": str(MAX_RESULTS),
            "key": api_key,
        },
    )
    video_ids = [
        item.get("id", {}).get("videoId")
        for item in search_data.get("items", [])
        if item.get("id", {}).get("videoId")
    ]
    if not video_ids:
        return []

    details = _request(
        "videos",
        {
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(video_ids),
            "maxResults": str(MAX_RESULTS),
            "key": api_key,
        },
    )
    by_id = {item["id"]: item for item in details.get("items", []) if item.get("id")}

    videos: list[dict[str, Any]] = []
    for video_id in video_ids:
        item = by_id.get(video_id)
        if not item:
            continue
        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})
        view_count = statistics.get("viewCount")
        thumbnails = snippet.get("thumbnails", {})
        thumbnail = next(
            (
                thumbnails[size].get("url")
                for size in ("high", "medium", "default")
                if thumbnails.get(size, {}).get("url")
            ),
            None,
        )
        videos.append(
            {
                "id": video_id,
                "title": snippet.get("title", "Untitled video"),
                "channelTitle": snippet.get("channelTitle", "Unknown channel"),
                "publishedAt": snippet.get("publishedAt"),
                "viewCount": int(view_count) if str(view_count).isdigit() else None,
                "duration": item.get("contentDetails", {}).get("duration"),
                "thumbnailUrl": thumbnail,
                "url": f"https://www.youtube.com/watch?v={video_id}",
            }
        )
    return videos


def _request(resource: str, params: dict[str, str]) -> dict[str, Any]:
    url = f"{API_ROOT}/{resource}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "topic-signals-mvp/0.1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        reason = _error_reason(error)
        if error.code in (403, 429) and reason in {
            "dailyLimitExceeded",
            "quotaExceeded",
            "rateLimitExceeded",
            "userRateLimitExceeded",
        }:
            raise YouTubeError(
                "quota_exceeded",
                "YouTube API quota is exhausted or temporarily rate-limited. Try again later.",
                429,
            ) from error
        if error.code in (400, 401, 403):
            raise YouTubeError(
                "youtube_api_error",
                "YouTube rejected the request. Check that the API key is valid and the YouTube Data API is enabled.",
            ) from error
        raise YouTubeError(
            "youtube_api_error",
            f"YouTube returned HTTP {error.code}. Try again later.",
        ) from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise YouTubeError(
            "youtube_unavailable",
            "YouTube could not be reached in time. Try again shortly.",
        ) from error
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise YouTubeError(
            "youtube_api_error",
            "YouTube returned an unreadable response. Try again later.",
        ) from error


def _error_reason(error: urllib.error.HTTPError) -> str | None:
    try:
        payload = json.loads(error.read().decode("utf-8"))
        errors = payload.get("error", {}).get("errors", [])
        return errors[0].get("reason") if errors else None
    except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
        return None
