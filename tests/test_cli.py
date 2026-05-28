from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from ytc import cli as ytc


def test_search_quiet_outputs_urls_only(capsys: pytest.CaptureFixture[str]) -> None:
    results = [
        ytc.SearchResult(
            phrase="xcodegen",
            title="XcodeGen Intro",
            upload_date="20250101",
            url="https://youtube.com/watch?v=abc123",
        ),
        ytc.SearchResult(
            phrase="xcodegen",
            title="XcodeGen Advanced",
            upload_date="20250102",
            url="https://youtube.com/watch?v=def456",
        ),
    ]
    with patch("ytc.cli.search", return_value=results):
        code = ytc.main(["search", "-q", "xcodegen"])
    assert code == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert out == [
        "https://youtube.com/watch?v=abc123",
        "https://youtube.com/watch?v=def456",
    ]


def test_transcript_reads_stdin_lines(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    stdin = io.StringIO("https://youtube.com/watch?v=abc123\nhttps://youtu.be/def456\n")
    monkeypatch.setattr(ytc.sys, "stdin", stdin)

    extracted: list[str] = []

    def fake_extract(value: str) -> str:
        extracted.append(value)
        return "abc123"

    monkeypatch.setattr(ytc, "extract_video_id", fake_extract)

    fake_snippet = SimpleNamespace(text="Hello world")
    fake_transcript = [fake_snippet]
    fetch_calls: list[str] = []

    def fake_fetch(self: object, video_id: str) -> list[SimpleNamespace]:
        fetch_calls.append(video_id)
        return fake_transcript

    with patch("youtube_transcript_api.YouTubeTranscriptApi.fetch", fake_fetch):
        code = ytc.main(["transcript"])
    assert code == 0
    assert len(fetch_calls) == 2
    assert extracted == [
        "https://youtube.com/watch?v=abc123",
        "https://youtu.be/def456",
    ]
    out_lines = capsys.readouterr().out.strip().splitlines()
    assert out_lines == ["Hello world", "Hello world"]


def test_bare_url_routes_to_transcript(capsys: pytest.CaptureFixture[str]) -> None:
    fake_snippet = SimpleNamespace(text="Hello from bare URL")

    def fake_fetch(self: object, video_id: str) -> list[SimpleNamespace]:
        assert video_id == "v5L2cRMcVYA"
        return [fake_snippet]

    with patch("youtube_transcript_api.YouTubeTranscriptApi.fetch", fake_fetch):
        code = ytc.main(["https://youtu.be/v5L2cRMcVYA"])

    assert code == 0
    assert capsys.readouterr().out.strip() == "Hello from bare URL"


def test_zsh_init_self_registers_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SHELL", "/bin/zsh")
    monkeypatch.setenv("ZDOTDIR", str(tmp_path))

    ytc._ensure_shell_init_registered()

    zshrc = tmp_path / ".zshrc"
    assert "alias ytc='noglob ytc'" in zshrc.read_text(encoding="utf-8")
    assert "Configured zsh for ytc unquoted URLs" in capsys.readouterr().err


def test_zsh_init_uses_custom_zdotdir_config_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "home"
    custom_zdotdir = tmp_path / "custom zsh config"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SHELL", "/bin/zsh")
    monkeypatch.setenv("ZDOTDIR", str(custom_zdotdir))

    ytc._ensure_shell_init_registered()

    custom_zshrc = custom_zdotdir / ".zshrc"
    default_zshrc = home / ".zshrc"
    assert custom_zshrc.exists()
    assert not default_zshrc.exists()
    assert "alias ytc='noglob ytc'" in custom_zshrc.read_text(encoding="utf-8")

    err = capsys.readouterr().err
    assert f"Configured zsh for ytc unquoted URLs in {custom_zshrc}" in err
    assert "Copy/paste this command once" in err
    assert "source " in err
    assert str(custom_zshrc) in err


def test_transcript_missing_input_returns_error(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ytc.sys, "stdin", io.StringIO(""))
    code = ytc.main(["transcript"])
    assert code == 2
    err = capsys.readouterr().err
    assert "missing <youtube_url_or_id>" in err
