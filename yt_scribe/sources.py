"""YouTube's official per-channel feed, which needs no API key."""

import urllib.request
from datetime import datetime
from xml.etree import ElementTree

from .types import Video

FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}


def parse_channel(xml: str) -> list[Video]:
    root = ElementTree.fromstring(xml)
    channel = (root.findtext("atom:title", "", NS) or "").strip()
    videos = []
    for entry in root.findall("atom:entry", NS):
        video_id = entry.findtext("yt:videoId", "", NS)
        if not video_id:
            continue
        videos.append(
            Video(
                id=video_id,
                url=f"https://www.youtube.com/watch?v={video_id}",
                title=(entry.findtext("atom:title", "", NS) or "").strip(),
                published=datetime.fromisoformat(
                    entry.findtext("atom:published", "", NS)
                ),
                channel=channel,
                # The feed's media:thumbnail is a maxres URL that 404s for many
                # videos; hqdefault always exists.
                thumbnail=f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
            )
        )
    return videos


def fetch_channel(channel_id: str, timeout: int = 30) -> list[Video]:
    with urllib.request.urlopen(
        FEED_URL.format(channel_id), timeout=timeout
    ) as response:
        return parse_channel(response.read().decode("utf-8"))
