from datetime import UTC
from pathlib import Path

from yt_scribe.sources import parse_channel

FIXTURE = Path(__file__).parent / "fixtures" / "channel.xml"


def test_parses_every_entry():
    videos = parse_channel(FIXTURE.read_text())
    assert len(videos) == 15


def test_fields_are_populated():
    first = parse_channel(FIXTURE.read_text())[0]
    assert len(first.id) == 11
    assert first.url == f"https://www.youtube.com/watch?v={first.id}"
    assert first.title
    assert first.channel
    assert first.published.tzinfo is not None
    assert first.published.astimezone(UTC)


def test_thumbnail_is_derived_from_the_id():
    first = parse_channel(FIXTURE.read_text())[0]
    assert first.thumbnail == f"https://i.ytimg.com/vi/{first.id}/hqdefault.jpg"
