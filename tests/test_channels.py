from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from ytc import cli


def test_channels_add_new(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    config = tmp_path / ".config" / "ytc" / "channels.json"
    monkeypatch.setattr("ytc.channels._CONFIG_PATH", config)

    with patch("ytc.channels._fetch_channel_name", return_value="Test Channel"):
        code = cli.main(["channels", "add", "UC_test123"])

    assert code == 0
    assert config.exists()
    data = json.loads(config.read_text())
    assert data["UC_test123"] == "Test Channel"
    out = capsys.readouterr().out
    assert "Test Channel" in out
    assert "UC_test123" in out


def test_channels_add_duplicate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    config = tmp_path / ".config" / "ytc" / "channels.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"UC_test123": "Test Channel"}))
    monkeypatch.setattr("ytc.channels._CONFIG_PATH", config)

    code = cli.main(["channels", "add", "UC_test123"])

    assert code == 0
    err = capsys.readouterr().err
    assert "already saved" in err


def test_channels_fetch_returns_ndjson(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fake_videos = [
        {"id": "vid001", "upload_date": "20250101", "like_count": 100},
        {"id": "vid002", "upload_date": "20250102", "like_count": 200},
    ]

    fake_snippet = MagicMock()
    fake_snippet.text = "hello world"

    with patch("ytc.channels._get_latest_video_ids", return_value=fake_videos):
        with patch("youtube_transcript_api.YouTubeTranscriptApi.fetch", return_value=[fake_snippet]):
            code = cli.main(["channels", "fetch", "UC_test123", "-n", "2"])

    assert code == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 2
    r1 = json.loads(lines[0])
    assert r1["id"] == "vid001"
    assert r1["transcript"] == "hello world"
    assert r1["likes"] == 100
    assert "url" in r1
    assert "date" in r1


def test_channels_fetch_default_n1(capsys: pytest.CaptureFixture[str]) -> None:
    fake_videos = [{"id": "vid001", "upload_date": "20250101", "like_count": 50}]
    fake_snippet = MagicMock()
    fake_snippet.text = "transcript text"

    with patch("ytc.channels._get_latest_video_ids", return_value=fake_videos) as mock_get:
        with patch("youtube_transcript_api.YouTubeTranscriptApi.fetch", return_value=[fake_snippet]):
            code = cli.main(["channels", "fetch", "UC_test123"])

    assert code == 0
    mock_get.assert_called_once_with("UC_test123", 1)


def test_channels_fetch_transcript_error_included_in_output(capsys: pytest.CaptureFixture[str]) -> None:
    fake_videos = [{"id": "vid001", "upload_date": "20250101", "like_count": None}]

    with patch("ytc.channels._get_latest_video_ids", return_value=fake_videos):
        with patch("youtube_transcript_api.YouTubeTranscriptApi.fetch", side_effect=Exception("no captions")):
            code = cli.main(["channels", "fetch", "UC_test123"])

    assert code == 1
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 1
    r = json.loads(lines[0])
    assert r["transcript"] is None
    assert "no captions" in r["error"]


def test_channels_missing_subcommand_returns_error(capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["channels"])
    assert code == 2
    assert "missing" in capsys.readouterr().err
