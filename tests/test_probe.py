from yt_scribe.probe import parse


def test_reads_both_fields():
    assert parse("not_live\n743\n") == ("not_live", 743)


def test_warnings_come_before_the_values():
    # yt-dlp prints warnings on stdout before what --print asked for; the
    # values are the last two lines.
    assert parse("WARNING: something\nis_live\nNA\n") == ("is_live", None)


def test_unknown_duration_is_none():
    # A live or upcoming video has no duration yet, and yt-dlp prints NA.
    assert parse("is_upcoming\nNA\n") == ("is_upcoming", None)


def test_fractional_duration_is_truncated():
    assert parse("not_live\n61.5\n") == ("not_live", 61)


def test_empty_output_is_unknown():
    assert parse("   \n") == ("unknown", None)


def test_one_line_is_unknown():
    # Fewer lines than fields means the print did not happen as asked; treat it
    # the same as no output rather than reading the duration as a status.
    assert parse("not_live\n") == ("unknown", None)
