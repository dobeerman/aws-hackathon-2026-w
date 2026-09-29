"""Lambda Function URL handler for the UI and search API."""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from grouping import group_videos
from youtube import YouTubeError, search_videos

ALLOWED_WINDOWS = {1, 3, 7, 14, 30}
MAX_TOPIC_LENGTH = 100
METHODOLOGY = (
    "Themes are deterministic groups from specific words and 2–3 word phrases "
    "repeated in at least two retrieved video titles. Promotional and editing terms "
    "are excluded; multiword phrases and cross-channel evidence are preferred. "
    "Unmatched videos remain in Other relevant signals. These are signals from this "
    "search—not a ranking of all YouTube trends. View counts are snapshots, not growth."
)
_cached_api_key: str | None = None


class ConfigurationError(Exception):
    pass


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    request_context = event.get("requestContext", {}).get("http", {})
    method = request_context.get("method", event.get("httpMethod", "GET"))
    path = event.get("rawPath", event.get("path", "/"))

    if method == "GET" and path in {"/", "/index.html"}:
        return _html_response()
    if method == "GET" and path == "/health":
        return _json_response(200, {"status": "ok"})
    if method == "POST" and path == "/api/search":
        return _search_response(event)
    return _json_response(
        404,
        {"error": {"code": "not_found", "message": "Route not found."}},
    )


def _search_response(event: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = _body(event)
        topic, days = _validate(payload)
        api_key = get_api_key()
        fetched_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        videos = search_videos(topic, days, api_key)
        themes = group_videos(videos, topic)
        return _json_response(
            200,
            {
                "query": topic,
                "windowDays": days,
                "fetchedAt": fetched_at,
                "resultCount": len(videos),
                "themes": themes,
                "methodology": METHODOLOGY,
                "notice": (
                    "YouTube's videoDuration=short filter selects short-duration "
                    "videos; it is not an exact YouTube Shorts classification."
                ),
                "emptyMessage": (
                    "No matching recent videos were returned. Try a broader topic "
                    "or a longer time window."
                    if not videos
                    else None
                ),
            },
        )
    except ValueError as error:
        return _error_response(400, "validation_error", str(error))
    except ConfigurationError as error:
        return _error_response(503, "configuration_error", str(error))
    except YouTubeError as error:
        return _error_response(error.status, error.code, error.message)
    except Exception:
        return _error_response(
            500,
            "internal_error",
            "The search could not be completed. Try again shortly.",
        )


def _body(event: dict[str, Any]) -> dict[str, Any]:
    raw_body = event.get("body")
    if not raw_body:
        raise ValueError("Request body must be JSON.")
    if event.get("isBase64Encoded"):
        raw_body = base64.b64decode(raw_body).decode("utf-8")
    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as error:
        raise ValueError("Request body must be valid JSON.") from error
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")
    return payload


def _validate(payload: dict[str, Any]) -> tuple[str, int]:
    topic = payload.get("topic")
    days = payload.get("days", 7)
    if not isinstance(topic, str) or not topic.strip():
        raise ValueError("Enter a topic.")
    topic = " ".join(topic.split())
    if len(topic) > MAX_TOPIC_LENGTH:
        raise ValueError(f"Topic must be {MAX_TOPIC_LENGTH} characters or fewer.")
    if (
        isinstance(days, bool)
        or not isinstance(days, int)
        or days not in ALLOWED_WINDOWS
    ):
        raise ValueError("Time window must be 1, 3, 7, 14, or 30 days.")
    return topic, days


def get_api_key() -> str:
    global _cached_api_key
    if _cached_api_key:
        return _cached_api_key

    local_key = os.getenv("YOUTUBE_API_KEY")
    if local_key:
        _cached_api_key = local_key
        return local_key

    secret_arn = os.getenv("YOUTUBE_API_KEY_SECRET_ARN")
    if not secret_arn:
        raise ConfigurationError(
            "YouTube API credentials are not configured. Set YOUTUBE_API_KEY "
            "locally or configure the deployment secret."
        )

    try:
        import boto3

        secret_value = boto3.client("secretsmanager").get_secret_value(
            SecretId=secret_arn
        )
        raw_secret = secret_value.get("SecretString")
        if not raw_secret:
            raise ConfigurationError(
                "The configured YouTube secret has no string value."
            )
        try:
            decoded = json.loads(raw_secret)
            key = decoded.get("apiKey") if isinstance(decoded, dict) else None
        except json.JSONDecodeError:
            key = raw_secret
        if not key or not isinstance(key, str):
            raise ConfigurationError(
                "The YouTube secret must be a raw key or JSON containing apiKey."
            )
        _cached_api_key = key
        return key
    except ConfigurationError:
        raise
    except Exception as error:
        raise ConfigurationError(
            "The YouTube API secret could not be read. Check its name and Lambda permission."
        ) from error


def _html_response() -> dict[str, Any]:
    html = Path(__file__).with_name("index.html").read_text(encoding="utf-8")
    return {
        "statusCode": 200,
        "headers": {
            "content-type": "text/html; charset=utf-8",
            "cache-control": "public, max-age=300",
            "x-content-type-options": "nosniff",
            "content-security-policy": (
                "default-src 'self'; img-src https://i.ytimg.com data:; "
                "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
                "connect-src 'self'; frame-ancestors 'none'"
            ),
        },
        "body": html,
    }


def _json_response(status: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {
            "content-type": "application/json; charset=utf-8",
            "cache-control": "no-store",
            "x-content-type-options": "nosniff",
        },
        "body": json.dumps(body, separators=(",", ":")),
    }


def _error_response(status: int, code: str, message: str) -> dict[str, Any]:
    return _json_response(status, {"error": {"code": code, "message": message}})
