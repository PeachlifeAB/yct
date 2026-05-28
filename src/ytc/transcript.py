from __future__ import annotations

import os


def make_api():
    from youtube_transcript_api import YouTubeTranscriptApi

    username = os.environ.get("WEBSHARE_USERNAME")
    password = os.environ.get("WEBSHARE_PASSWORD")

    if username and password:
        from youtube_transcript_api.proxies import WebshareProxyConfig
        return YouTubeTranscriptApi(
            proxy_config=WebshareProxyConfig(
                proxy_username=username,
                proxy_password=password,
            )
        )

    return YouTubeTranscriptApi()


def fetch_transcript(video_id: str):
    return make_api().fetch(video_id)
