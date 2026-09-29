"""Transparent, deterministic grouping for retrieved YouTube videos."""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from typing import Any

TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9'+-]{2,}")
STOP_WORDS = {
    "about",
    "after",
    "again",
    "against",
    "best",
    "could",
    "from",
    "have",
    "here",
    "into",
    "just",
    "latest",
    "more",
    "most",
    "new",
    "now",
    "official",
    "short",
    "shorts",
    "that",
    "their",
    "there",
    "these",
    "this",
    "today",
    "video",
    "what",
    "when",
    "where",
    "which",
    "with",
    "would",
    "youtube",
    "your",
}


def _tokens(text: str, topic_words: set[str]) -> list[str]:
    return [
        token
        for token in TOKEN_PATTERN.findall(text.lower())
        if token not in STOP_WORDS and token not in topic_words
    ]


def _candidates(title: str, topic_words: set[str]) -> set[str]:
    words = _tokens(title, topic_words)
    candidates = set(words)
    candidates.update(f"{left} {right}" for left, right in zip(words, words[1:]))
    return candidates


def _views(video: dict[str, Any]) -> int:
    value = video.get("viewCount")
    return value if isinstance(value, int) else 0


def _published_timestamp(video: dict[str, Any]) -> float:
    try:
        return datetime.fromisoformat(
            video["publishedAt"].replace("Z", "+00:00")
        ).timestamp()
    except (KeyError, TypeError, ValueError):
        return 0


def group_videos(
    videos: list[dict[str, Any]], topic: str, max_themes: int = 4
) -> list[dict[str, Any]]:
    """Group videos by repeated title phrases without generating new facts."""

    if not videos:
        return []

    topic_words = set(TOKEN_PATTERN.findall(topic.lower()))
    per_video = [_candidates(video.get("title", ""), topic_words) for video in videos]
    document_frequency = Counter(
        candidate for candidates in per_video for candidate in candidates
    )

    def candidate_rank(candidate: str) -> tuple[int, int, int, str]:
        supporters = [
            video
            for video, candidates in zip(videos, per_video)
            if candidate in candidates
        ]
        return (
            document_frequency[candidate],
            sum(_views(video) for video in supporters),
            len(candidate.split()),
            candidate,
        )

    repeated = [
        candidate for candidate, count in document_frequency.items() if count >= 2
    ]
    repeated.sort(key=candidate_rank, reverse=True)

    selected: list[str] = []
    selected_words: set[str] = set()
    for candidate in repeated:
        words = set(candidate.split())
        if words & selected_words:
            continue
        selected.append(candidate)
        selected_words.update(words)
        if len(selected) == max_themes:
            break

    assignments: dict[str, list[dict[str, Any]]] = {
        candidate: [] for candidate in selected
    }
    other: list[dict[str, Any]] = []

    for video, candidates in zip(videos, per_video):
        matches = [candidate for candidate in selected if candidate in candidates]
        if matches:
            strongest = max(matches, key=candidate_rank)
            assignments[strongest].append(video)
        else:
            other.append(video)

    groups: list[dict[str, Any]] = []
    for candidate, supporting_videos in assignments.items():
        if not supporting_videos:
            continue
        groups.append(_make_theme(candidate.title(), supporting_videos, candidate))

    if other:
        groups.append(
            _make_theme(
                "Other relevant signals",
                other,
                "No repeated selected title phrase matched these videos",
            )
        )

    groups.sort(
        key=lambda group: (
            group["videoCount"],
            group["availableViewTotal"],
            group["newestPublishedAt"],
        ),
        reverse=True,
    )
    return groups[: max_themes + 1]


def _make_theme(
    label: str, videos: list[dict[str, Any]], evidence: str
) -> dict[str, Any]:
    sorted_videos = sorted(
        videos,
        key=lambda video: (_views(video), _published_timestamp(video)),
        reverse=True,
    )
    newest = max(
        (video.get("publishedAt", "") for video in videos),
        default="",
    )
    available_views = [
        _views(video) for video in videos if video.get("viewCount") is not None
    ]
    return {
        "label": label,
        "why": (
            f"{len(videos)} retrieved video title(s) support this group; "
            f"evidence: {evidence}."
        ),
        "videoCount": len(videos),
        "availableViewTotal": sum(available_views),
        "availableViewSamples": len(available_views),
        "newestPublishedAt": newest,
        "videos": sorted_videos,
    }
