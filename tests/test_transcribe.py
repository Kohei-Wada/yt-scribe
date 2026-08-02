from yt_scribe.transcribe import live_status


def test_reads_the_last_line():
    # yt-dlp prints warnings before the value; the value is the last line.
    assert live_status("WARNING: something\nis_live\n") == "is_live"


def test_plain_value():
    assert live_status("not_live\n") == "not_live"


def test_empty_output_is_unknown():
    assert live_status("   \n") == "unknown"
