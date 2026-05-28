from __future__ import annotations

import re
from typing import Final

_RAW_ID_RE: Final = re.compile(r"^[A-Za-z0-9_-]{11}$")
_QUERY_RE: Final = re.compile(r"[?&](?:v|vi)=([A-Za-z0-9_-]{11})")
_PATH_RE: Final = re.compile(r"(?:youtu\.be/|/(?:embed|shorts|live|v|vi|e)/)([A-Za-z0-9_-]{11})")
_ATTR_RE: Final = re.compile(r"(?:v%3D|vi%3D)([A-Za-z0-9_-]{11})")


def extract_video_id(value: str) -> str | None:
    if _RAW_ID_RE.fullmatch(value):
        return value

    m = _QUERY_RE.search(value)
    if m:
        return m.group(1)

    m = _PATH_RE.search(value)
    if m:
        return m.group(1)

    m = _ATTR_RE.search(value)
    if m:
        return m.group(1)

    return None
