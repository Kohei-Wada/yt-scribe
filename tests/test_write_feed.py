import os
import stat

from yt_scribe.__main__ import write_feed


def test_written_feed_is_readable_by_group_and_other(tmp_path):
    path = tmp_path / "feed.xml"
    previous = os.umask(0o022)
    try:
        write_feed(str(path), "<feed/>")
    finally:
        os.umask(previous)
    mode = stat.S_IMODE(path.stat().st_mode)
    assert mode == 0o644, oct(mode)


def test_umask_is_respected(tmp_path):
    path = tmp_path / "feed.xml"
    previous = os.umask(0o077)
    try:
        write_feed(str(path), "<feed/>")
    finally:
        os.umask(previous)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
