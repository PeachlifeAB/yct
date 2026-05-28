from __future__ import annotations

import json
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from ._extract import extract_video_id

_CONFIG_PATH = Path.home() / ".config" / "ytc" / "channels.json"


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def _load_channels() -> dict[str, str]:
    """Return {channel_id: label} dict from config file."""
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_channels(channels: dict[str, str]) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(json.dumps(channels, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------

def cmd_add(channel_id: str) -> int:
    channels = _load_channels()
    if channel_id in channels:
        print(f"{channel_id} already saved.", file=sys.stderr)
        return 0
    # Fetch channel name via yt-dlp to use as label
    label = _fetch_channel_name(channel_id) or channel_id
    channels[channel_id] = label
    _save_channels(channels)
    print(f"Added: {label} ({channel_id})")
    return 0


def _fetch_channel_name(channel_id: str) -> str | None:
    from yt_dlp import YoutubeDL
    from typing import cast

    opts = cast(Any, {"quiet": True, "no_warnings": True, "extract_flat": True})
    url = f"https://www.youtube.com/channel/{channel_id}"
    with YoutubeDL(opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            if info:
                return info.get("uploader") or info.get("channel") or None
        except Exception:
            pass
    return None


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

def cmd_search(keywords: list[str]) -> int:
    from yt_dlp import YoutubeDL
    from typing import cast

    query = " ".join(keywords)

    # Step 1: search for videos, collect unique channels (capped at 5 unique)
    search_opts = cast(Any, {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
    })
    channel_ids: list[str] = []
    seen: set[str] = set()
    with YoutubeDL(search_opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch20:{query}", download=False)
            if info and "entries" in info:
                for entry in info["entries"]:
                    if not entry:
                        continue
                    cid = entry.get("channel_id") or entry.get("uploader_id") or ""
                    if cid and cid not in seen:
                        seen.add(cid)
                        channel_ids.append(cid)
                    if len(channel_ids) >= 5:
                        break
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    if not channel_ids:
        print("No channels found.", file=sys.stderr)
        return 1

    # Step 2: fetch metadata for each channel
    meta_opts = cast(Any, {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "playlistend": 1,
    })
    records = []
    for cid in channel_ids:
        url = f"https://www.youtube.com/channel/{cid}"
        with YoutubeDL(meta_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                if not info:
                    continue
                name = info.get("uploader") or info.get("channel") or cid
                followers = info.get("channel_follower_count")
                top_entries = info.get("entries") or []
                first_entry = top_entries[0] if top_entries else None
                video_entries = (first_entry or {}).get("entries") or [] if isinstance(first_entry, dict) else []
                first_video = video_entries[0] if video_entries else first_entry
                last_video = ""
                if first_video:
                    last_video = first_video.get("upload_date", "") or ""
                    if not last_video:
                        vid_url = first_video.get("url") or first_video.get("webpage_url") or ""
                        if vid_url:
                            try:
                                vid_info = ydl.extract_info(vid_url, download=False)
                                last_video = (vid_info or {}).get("upload_date", "") or ""
                            except Exception:
                                pass
                records.append({
                    "name": name,
                    "id": cid,
                    "channel_url": f"https://www.youtube.com/channel/{cid}",
                    "followers": followers,
                    "last_video": last_video or None,
                })
            except Exception:
                continue

    # Rank by name similarity to query (1 = closest)
    q = query.lower()
    records.sort(
        key=lambda r: SequenceMatcher(None, q, r["name"].lower()).ratio(),
        reverse=True,
    )
    for rank, record in enumerate(records, start=1):
        record["rank"] = rank
        print(json.dumps(record, ensure_ascii=False))

    return 0


# ---------------------------------------------------------------------------
# fetch
# ---------------------------------------------------------------------------

def cmd_fetch(channel_id: str, n: int) -> int:
    """Fetch transcripts for the last n videos from a channel."""
    video_ids = _get_latest_video_ids(channel_id, n)
    if not video_ids:
        print(f"ERROR: No videos found for channel {channel_id}", file=sys.stderr)
        return 1

    from .transcript import fetch_transcript

    exit_code = 0
    for vid in video_ids:
        url = f"https://www.youtube.com/watch?v={vid['id']}"
        try:
            transcript = fetch_transcript(vid["id"])
            text = " ".join(s.text for s in transcript)
            record = {
                "id": vid["id"],
                "date": vid.get("upload_date", ""),
                "likes": vid.get("like_count"),
                "url": url,
                "transcript": text,
            }
            print(json.dumps(record, ensure_ascii=False))
        except Exception as exc:
            record = {
                "id": vid["id"],
                "date": vid.get("upload_date", ""),
                "likes": vid.get("like_count"),
                "url": url,
                "transcript": None,
                "error": str(exc),
            }
            print(json.dumps(record, ensure_ascii=False))
            exit_code = 1

    return exit_code


def _get_latest_video_ids(channel_id: str, n: int) -> list[dict[str, Any]]:
    from yt_dlp import YoutubeDL
    from typing import cast

    opts = cast(Any, {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "playlistend": n,
    })
    url = f"https://www.youtube.com/channel/{channel_id}/videos"
    with YoutubeDL(opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            if info and "entries" in info:
                results = []
                for entry in info["entries"]:
                    if not entry:
                        continue
                    vid_id = entry.get("id") or extract_video_id(entry.get("url", ""))
                    if vid_id:
                        results.append({
                            "id": vid_id,
                            "upload_date": entry.get("upload_date", ""),
                            "like_count": entry.get("like_count"),
                        })
                return results
        except Exception:
            pass
    return []
