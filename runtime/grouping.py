"""Transparent, deterministic grouping for retrieved YouTube videos."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9'+-]{2,}")
GENERIC_WORDS = {
    "about",
    "after",
    "again",
    "against",
    "amazing",
    "banaye",
    "best",
    "capcut",
    "clip",
    "clips",
    "could",
    "edit",
    "editing",
    "edits",
    "effect",
    "effects",
    "from",
    "generated",
    "generator",
    "have",
    "here",
    "how",
    "instagram",
    "into",
    "just",
    "kaise",
    "latest",
    "make",
    "more",
    "most",
    "new",
    "now",
    "official",
    "prompt",
    "prompts",
    "reel",
    "reels",
    "short",
    "shorts",
    "that",
    "their",
    "there",
    "these",
    "this",
    "tiktok",
    "today",
    "trend",
    "trending",
    "tutorial",
    "tutorials",
    "use",
    "using",
    "video",
    "videos",
    "viral",
    "what",
    "when",
    "where",
    "which",
    "with",
    "would",
    "youtube",
    "your",
}


def _specific_runs(text: str, topic_words: set[str]) -> list[list[str]]:
    runs: list[list[str]] = []
    current: list[str] = []
    for token in TOKEN_PATTERN.findall(text.lower()):
        if token in GENERIC_WORDS or token in topic_words:
            if current:
                runs.append(current)
                current = []
        else:
            current.append(token)
    if current:
        runs.append(current)
    return runs


def _candidates(title: str, topic_words: set[str]) -> set[str]:
    runs = _specific_runs(title, topic_words)
    candidates = {word for run in runs for word in run}
    for words in runs:
        for size in (2, 3):
            for index in range(len(words) - size + 1):
                phrase_words = words[index : index + size]
                if len(set(phrase_words)) == size:
                    candidates.add(" ".join(phrase_words))
    return candidates


def _candidate_position(title: str, candidate: str) -> int:
    words = TOKEN_PATTERN.findall(title.lower())
    phrase_words = candidate.split()
    size = len(phrase_words)
    for index in range(len(words) - size + 1):
        if words[index : index + size] == phrase_words:
            return index
    return len(words)


def _channel(video: dict[str, Any]) -> str:
    value = video.get("channelTitle")
    return value.strip().casefold() if isinstance(value, str) else ""


def _has_cross_channel_support(
    supporter_indexes: set[int], videos: list[dict[str, Any]]
) -> bool:
    channels = [_channel(videos[index]) for index in supporter_indexes]
    known_channels = {channel for channel in channels if channel}
    return len(known_channels) >= 2 or any(not channel for channel in channels)


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
    supporters_by_candidate: dict[str, set[int]] = {}
    for index, candidates in enumerate(per_video):
        for candidate in candidates:
            supporters_by_candidate.setdefault(candidate, set()).add(index)

    def candidate_rank(candidate: str) -> tuple[int, int, int, int, int, str]:
        supporter_indexes = supporters_by_candidate[candidate]
        channels = {_channel(videos[index]) for index in supporter_indexes}
        channels.discard("")
        word_count = len(candidate.split())
        position_total = sum(
            _candidate_position(videos[index].get("title", ""), candidate)
            for index in supporter_indexes
        )
        return (
            1 if word_count >= 2 else 0,
            word_count,
            len(channels),
            len(supporter_indexes),
            -position_total,
            candidate,
        )

    eligible = [
        candidate
        for candidate, supporter_indexes in supporters_by_candidate.items()
        if len(supporter_indexes) >= 2
        and _has_cross_channel_support(supporter_indexes, videos)
    ]
    eligible.sort(key=candidate_rank, reverse=True)

    selected: list[tuple[str, set[int]]] = []
    claimed: set[int] = set()
    for candidate in eligible:
        available_supporters = supporters_by_candidate[candidate] - claimed
        if len(available_supporters) < 2:
            continue
        if not _has_cross_channel_support(available_supporters, videos):
            continue
        selected.append((candidate, available_supporters))
        claimed.update(available_supporters)
        if len(selected) == max_themes:
            break

    groups: list[dict[str, Any]] = []
    for candidate, supporter_indexes in selected:
        supporting_videos = [videos[index] for index in sorted(supporter_indexes)]
        channel_count = len({_channel(video) for video in supporting_videos} - {""})
        groups.append(
            _make_theme(
                candidate.title(),
                supporting_videos,
                f'phrase "{candidate}" appears across {channel_count} channel(s)',
            )
        )

    other = [video for index, video in enumerate(videos) if index not in claimed]
    if other:
        groups.append(
            _make_theme(
                "Other relevant signals",
                other,
                "No repeated selected title phrase matched these videos",
            )
        )

    return groups


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
