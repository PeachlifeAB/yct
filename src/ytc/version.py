from __future__ import annotations

from importlib.metadata import version


def cli_version(dist_name: str = "ytc") -> str:
    """Return version string for `ytc --version`.

    Format: ytc X.Y.devN+gHHHHHHH.dYYYYMMDDHHMMSS
    - In editable installs: includes git hash and timestamp
    - In releases: semver tag (e.g., 1.0.0)
    """
    try:
        return version(dist_name)
    except Exception:
        return "unknown"
