from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


def _strip_ansi(s: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", s)


def _uv_env() -> dict[str, str]:
    """Env dict that disables color output from uv."""
    return {**os.environ, "NO_COLOR": "1", "PYTHONUTF8": "1"}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_editable_install_cli_is_executable(tmp_path: Path) -> None:
    """Verify the installed CLI is executable and returns help."""
    if sys.platform.startswith("win"):
        raise RuntimeError("Windows not supported by this test")

    repo_root = _repo_root()

    env = _uv_env()
    tool_bin = Path(
        _strip_ansi(
            subprocess.check_output(["uv", "tool", "dir", "--bin"], env=env)
            .decode()
            .strip()
        )
    )
    ytc_path = tool_bin / "ytc"

    backup_path = None
    if ytc_path.exists() or ytc_path.is_symlink():
        backup_path = tmp_path / "ytc.backup"
        ytc_path.replace(backup_path)

    try:
        subprocess.check_call(
            [
                "uv",
                "tool",
                "install",
                "--force",
                "--editable",
                str(repo_root),
                "--no-binary-package",
                "charset-normalizer",
            ],
            env=env,
        )

        result = subprocess.run(
            [str(ytc_path), "--help"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0, (
            f"CLI returned code {result.returncode}: {result.stderr}"
        )
        assert "--version" in result.stdout
        assert "search" in result.stdout
    finally:
        if backup_path is not None:
            backup_path.replace(ytc_path)


def test_editable_install_cli_imports_main(tmp_path: Path) -> None:
    """Verify the ytc package can be imported and main function is accessible."""
    if sys.platform.startswith("win"):
        raise RuntimeError("Windows not supported by this test")

    repo_root = _repo_root()

    env = _uv_env()
    tool_bin = Path(
        _strip_ansi(
            subprocess.check_output(["uv", "tool", "dir", "--bin"], env=env)
            .decode()
            .strip()
        )
    )
    ytc_path = tool_bin / "ytc"

    backup_path = None
    if ytc_path.exists() or ytc_path.is_symlink():
        backup_path = tmp_path / "ytc.backup"
        ytc_path.replace(backup_path)

    try:
        subprocess.check_call(
            [
                "uv",
                "tool",
                "install",
                "--force",
                "--editable",
                str(repo_root),
                "--no-binary-package",
                "charset-normalizer",
            ],
            env=env,
        )

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from ytc.cli import main; print('Import successful')",
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0, f"Import failed: {result.stderr}"
        assert "Import successful" in result.stdout
    finally:
        if backup_path is not None:
            backup_path.replace(ytc_path)


def test_editable_install_version_format(tmp_path: Path) -> None:
    """Verify the installed version has correct format: ytc X.Y.devN+gHHHHHHH.dYYYYMMDDHHMMSS."""
    if sys.platform.startswith("win"):
        raise RuntimeError("Windows not supported by this test")

    repo_root = _repo_root()

    env = _uv_env()
    tool_bin = Path(
        _strip_ansi(
            subprocess.check_output(["uv", "tool", "dir", "--bin"], env=env)
            .decode()
            .strip()
        )
    )
    ytc_path = tool_bin / "ytc"

    backup_path = None
    if ytc_path.exists() or ytc_path.is_symlink():
        backup_path = tmp_path / "ytc.backup"
        ytc_path.replace(backup_path)

    try:
        subprocess.check_call(
            [
                "uv",
                "tool",
                "install",
                "--force",
                "--editable",
                str(repo_root),
                "--no-binary-package",
                "charset-normalizer",
            ],
            env=env,
        )

        out = (
            subprocess.check_output(
                [str(ytc_path), "--version"],
                cwd=repo_root,
                env=env,
            )
            .decode()
            .strip()
        )

        assert out.startswith("ytc "), f"Version should start with 'ytc ': {out}"

        assert "+g" in out, f"Version should contain '+g' for git hash: {out}"
        hash_part = out.split("+g")[1][:7]
        assert len(hash_part) == 7, f"Git hash should be 7 chars: {hash_part}"
        assert all(c in "0123456789abcdef" for c in hash_part), (
            f"Git hash should be hex: {hash_part}"
        )

        assert ".d20" in out, f"Version should contain '.d20' for timestamp: {out}"
        timestamp = out.rsplit(".d", 1)[1]
        assert len(timestamp) == 14, (
            f"Timestamp should be 14 chars, got {len(timestamp)}: {timestamp}"
        )
        assert timestamp.isdigit(), f"Timestamp should be all digits: {timestamp}"
    finally:
        if backup_path is not None:
            backup_path.replace(ytc_path)
