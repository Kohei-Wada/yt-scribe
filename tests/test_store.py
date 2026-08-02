from datetime import UTC, datetime

from yt_scribe.store import Store
from yt_scribe.types import Video


def make_video(video_id="abc123", minute=0):
    return Video(
        id=video_id,
        url=f"https://www.youtube.com/watch?v={video_id}",
        title=f"Title {video_id}",
        published=datetime(2026, 8, 2, 12, minute, tzinfo=UTC),
        channel="Channel",
        thumbnail=None,
    )


def test_unknown_video_is_not_done(tmp_path):
    store = Store(tmp_path / "s.db")
    assert store.is_done("abc123") is False


def test_saved_video_is_done(tmp_path):
    store = Store(tmp_path / "s.db")
    store.save(make_video(), "transcript", None)
    assert store.is_done("abc123") is True


def test_entries_are_newest_first(tmp_path):
    store = Store(tmp_path / "s.db")
    store.save(make_video("old00000000", minute=0), "t", None)
    store.save(make_video("new00000000", minute=30), "t", None)
    assert [e["id"] for e in store.entries()] == ["new00000000", "old00000000"]


def test_entry_round_trips_its_fields(tmp_path):
    store = Store(tmp_path / "s.db")
    store.save(make_video(), "the transcript", "the summary")
    entry = store.entries()[0]
    assert entry["transcript"] == "the transcript"
    assert entry["summary"] == "the summary"
    assert entry["title"] == "Title abc123"


def test_saving_twice_does_not_duplicate(tmp_path):
    store = Store(tmp_path / "s.db")
    store.save(make_video(), "first", None)
    store.save(make_video(), "second", None)
    assert len(store.entries()) == 1
    assert store.entries()[0]["transcript"] == "second"
