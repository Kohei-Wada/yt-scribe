from datetime import UTC, datetime

from yt_scribe.types import Video


def test_video_is_frozen():
    v = Video(
        id="abc123",
        url="https://www.youtube.com/watch?v=abc123",
        title="A title",
        published=datetime(2026, 8, 2, tzinfo=UTC),
        channel="Some Channel",
        thumbnail=None,
    )
    assert v.id == "abc123"
    try:
        v.id = "other"
    except AttributeError:
        return
    raise AssertionError("Video should be immutable")
