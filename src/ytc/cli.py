from __future__ import annotations

import argparse
import os
import shlex
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NamedTuple, cast

from ._extract import extract_video_id
from .version import cli_version


class SearchResult(NamedTuple):
    """Represents a YouTube search result."""

    phrase: str
    title: str
    upload_date: str
    url: str
    channel: str = ""
    channel_id: str = ""
    like_count: int | None = None


def _format_like_count(like_count: int | None) -> str:
    if like_count is None:
        return "likes unavailable"
    return f"{like_count:,} likes"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ytc",
        description="Fetch YouTube transcripts and search for videos.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--version",
        action="store_true",
        help="Print version (dev: git short hash; releases: semver tag)",
    )
    subparsers = p.add_subparsers(dest="command", help="Subcommands")

    # Search subcommand
    search_parser = subparsers.add_parser(
        "search",
        help="Search YouTube for videos",
        epilog="Example: ytc search python tutorial beginner",
    )
    search_parser.add_argument(
        "keywords",
        nargs="+",
        help="Keywords to search (space-separated, NOT quoted)",
    )
    search_parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Output only URLs (one per line)",
    )

    # Transcript subcommand (original behavior)
    transcript_parser = subparsers.add_parser(
        "transcript",
        help="Fetch transcript for a YouTube video",
    )
    transcript_parser.add_argument(
        "input",
        nargs="?",
        help="YouTube URL or 11-char video id (or read from stdin)",
    )

    # Channels subcommand
    channels_parser = subparsers.add_parser(
        "channels",
        help="Manage and fetch from saved YouTube channels",
    )
    channels_sub = channels_parser.add_subparsers(dest="channels_command")

    ch_add = channels_sub.add_parser("add", help="Save a channel ID to ~/.config/ytc/channels.json")
    ch_add.add_argument("channel_id", help="YouTube channel ID")

    ch_search = channels_sub.add_parser("search", help="Search YouTube for channels")
    ch_search.add_argument("keywords", nargs="+", help="Keywords to search")

    ch_fetch = channels_sub.add_parser("fetch", help="Fetch transcripts from a channel (JSON output)")
    ch_fetch.add_argument("channel_id", help="YouTube channel ID")
    ch_fetch.add_argument(
        "-n",
        type=int,
        default=1,
        metavar="N",
        help="Number of latest videos to fetch (default: 1)",
    )

    return p


def _search_yt_dlp(query: str) -> list[SearchResult]:
    """Search YouTube using yt-dlp and return list of SearchResult."""
    from yt_dlp import YoutubeDL

    ydl_opts = cast(
        Any,
        {
            "quiet": True,
            "no_warnings": True,
            "format": "best",
        },
    )

    with YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch10:{query}", download=False)
            if info and "entries" in info:
                return [
                    SearchResult(
                        phrase=query,
                        title=entry.get("title", "") or "",
                        upload_date=entry.get("upload_date", "") or "",
                        url=entry.get("webpage_url", "") or "",
                        channel=entry.get("uploader", entry.get("channel", "")) or "",
                        channel_id=entry.get("channel_id", entry.get("uploader_id", ""))
                        or "",
                        like_count=entry.get("like_count"),
                    )
                    for entry in info["entries"]
                    if entry
                ]
        except Exception:
            pass
    return []


def search(keywords: Sequence[str]) -> list[SearchResult]:
    """
    Search YouTube with prioritized keywords as a phrase.

    Searches all keywords as a phrase first. If no results, removes the last
    keyword and searches again. Repeats until results found or only the first
    keyword remains. If still no results, returns empty list.

    Args:
        keywords: Sequence of prioritized keywords (first = highest priority)

    Returns:
        List of SearchResult found, or empty list if none found.
    """
    if not keywords:
        return []

    phrases: list[str] = []
    for i in range(len(keywords), 0, -1):
        phrase = " ".join(keywords[:i])
        phrases.append(phrase)

    for phrase in phrases:
        results = _search_yt_dlp(phrase)
        if results:
            return results
        if phrase != phrases[-1]:
            time.sleep(0.5)

    return []


_ZSH_INIT = "alias ytc='noglob ytc'"
_FISH_INIT = "alias ytc 'noglob ytc'"


def _detect_shell() -> str:
    shell_path = os.environ.get("SHELL", "")
    if "zsh" in shell_path:
        return "zsh"
    if "fish" in shell_path:
        return "fish"
    return "bash"


def _zshrc_path() -> Path:
    zdotdir = os.environ.get("ZDOTDIR")
    if zdotdir:
        return Path(zdotdir).expanduser() / ".zshrc"
    return Path.home() / ".zshrc"


def _fish_config_path() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        return Path(config_home) / "fish" / "config.fish"
    return Path.home() / ".config" / "fish" / "config.fish"


def _zsh_init_is_registered() -> bool:
    try:
        content = _zshrc_path().read_text(encoding="utf-8")
    except OSError:
        return False
    return any(
        p in content
        for p in (
            "alias ytc='noglob ytc'",
            'alias ytc="noglob ytc"',
            'eval "$(ytc init)"',
            "eval '$(ytc init)'",
            'eval "$(ytc init zsh)"',
            "eval '$(ytc init zsh)'",
        )
    )


def _fish_init_is_registered() -> bool:
    try:
        content = _fish_config_path().read_text(encoding="utf-8")
    except OSError:
        return False
    return "alias ytc" in content


def _ensure_shell_init_registered() -> None:
    shell = _detect_shell()

    if shell == "zsh" and not _zsh_init_is_registered():
        rc = _zshrc_path()
        source_command = f"source {shlex.quote(str(rc))}"
        rc.parent.mkdir(parents=True, exist_ok=True)
        with rc.open("a", encoding="utf-8") as fh:
            fh.write(
                "\n# ytc: allow unquoted YouTube URLs containing ? in zsh\n"
                f"# To activate immediately in the current shell, run: {source_command}\n"
                f"{_ZSH_INIT}\n"
            )
        print(
            f"Configured zsh for ytc unquoted URLs in {rc}.\n"
            "A child process cannot source the already-running parent zsh.\n"
            "Copy/paste this command once to activate it in the current shell:\n"
            f"  {source_command}",
            file=sys.stderr,
        )

    elif shell == "fish" and not _fish_init_is_registered():
        cfg = _fish_config_path()
        cfg.parent.mkdir(parents=True, exist_ok=True)
        with cfg.open("a", encoding="utf-8") as fh:
            fh.write(
                "\n# ytc: allow unquoted YouTube URLs containing ? in fish\n"
                f"{_FISH_INIT}\n"
            )
        print(
            f"Configured fish for ytc unquoted URLs in {cfg}.\n"
            "Run 'exec fish' or open a new terminal to activate.",
            file=sys.stderr,
        )


def main(argv: list[str] | None = None) -> int:
    # Auto-route: if first non-flag argument isn't a known subcommand, treat
    # it as a transcript URL/ID input (so bare URLs work without 'transcript').
    called_from_cli = argv is None
    if argv is None:
        argv = sys.argv[1:] if sys.argv[1:] else []
    known_commands = {"search", "transcript", "channels"}
    non_flag_args = [a for a in argv if not a.startswith("-")]
    if non_flag_args and non_flag_args[0] not in known_commands:
        argv = ["transcript"] + argv

    args = _build_parser().parse_args(argv)

    if called_from_cli:
        _ensure_shell_init_registered()

    if args.version:
        print(f"ytc {cli_version()}")
        return 0

    if args.command == "search":
        # Handle both space-separated keywords and quoted phrases
        keywords = []
        for kw in args.keywords:
            # If keyword contains spaces (quoted by user), split it
            if " " in kw:
                keywords.extend(kw.split())
            else:
                keywords.append(kw)
        results = search(keywords)
        if results:
            for result in results:
                if args.quiet:
                    print(result.url)
                else:
                    print(result.phrase)
                    print(result.title)
                    print(result.upload_date)
                    print(result.url)
                    print(result.channel)
                    print(result.channel_id)
                    print(_format_like_count(result.like_count))
                    print()
        else:
            print("No results found.", file=sys.stderr)
            return 1
        return 0

    if args.command == "transcript":
        raw_input = args.input
        if raw_input is None:
            raw_input = sys.stdin.read().strip()

        if not raw_input:
            print("ERROR: missing <youtube_url_or_id>", file=sys.stderr)
            return 2

        # Support multiple URLs/IDs from stdin (one per line)
        inputs = [line.strip() for line in raw_input.splitlines() if line.strip()]
        if not inputs:
            print("ERROR: missing <youtube_url_or_id>", file=sys.stderr)
            return 2

        from .transcript import fetch_transcript

        exit_code = 0
        for item in inputs:
            video_id = extract_video_id(item)
            if not video_id:
                print(
                    f"ERROR: Could not extract a YouTube video id from: {item}",
                    file=sys.stderr,
                )
                print(
                    "Expected an 11-char id or a URL containing v=<id>/vi=<id>, youtu.be/<id>, /(embed|shorts|live|v|vi|e)/<id>, or attribution_link with v%3D<id>.",
                    file=sys.stderr,
                )
                exit_code = 2
                continue

            try:
                transcript = fetch_transcript(video_id)
                for snippet in transcript:
                    print(snippet.text)
            except Exception as exc:
                print(
                    f"ERROR: Could not retrieve transcript for {video_id}: {exc}",
                    file=sys.stderr,
                )
                exit_code = 1

        return exit_code

    if args.command == "channels":
        from .channels import cmd_add, cmd_search, cmd_fetch
        if args.channels_command == "add":
            return cmd_add(args.channel_id)
        if args.channels_command == "search":
            return cmd_search(args.keywords)
        if args.channels_command == "fetch":
            return cmd_fetch(args.channel_id, args.n)
        print("ERROR: missing channels subcommand (add, search, fetch)", file=sys.stderr)
        return 2

    # Legacy mode: no subcommand, treat first arg as input
    if args.command is None and not args.version:
        print("ERROR: missing <youtube_url_or_id>", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
