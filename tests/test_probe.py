import subprocess

import pytest

from yt_scribe import probe as probe_module
from yt_scribe.probe import not_yet_live, parse, probe


def install_fake(monkeypatch, returncode, stdout="", stderr=""):
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, returncode, stdout, stderr)

    monkeypatch.setattr(probe_module.subprocess, "run", fake_run)


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


def test_stream_about_to_start_is_not_yet_live():
    # yt-dlp exits non-zero and prints nothing for a scheduled stream, so the
    # status never reaches parse().
    assert not_yet_live(
        "ERROR: [youtube] lyx5HGd8afo: This live event will begin in a few moments.\n"
    )


def test_premiere_is_not_yet_live():
    assert not_yet_live("ERROR: [youtube] abc123: Premieres in 3 hours\n")


def test_unavailable_video_is_an_ordinary_failure():
    assert not not_yet_live("ERROR: [youtube] abc123: Video unavailable\n")


def test_probe_reports_a_scheduled_stream_as_upcoming(monkeypatch):
    # Skipped like any other upcoming stream, so the next run picks it up once
    # the recording exists, instead of counting as a failure every night.
    install_fake(
        monkeypatch,
        1,
        stderr="ERROR: [youtube] lyx5HGd8afo: This live event will begin in a few moments.\n",
    )
    assert probe("https://www.youtube.com/watch?v=lyx5HGd8afo") == ("is_upcoming", None)


def test_probe_raises_on_any_other_error(monkeypatch):
    install_fake(monkeypatch, 1, stderr="ERROR: [youtube] abc123: Video unavailable\n")
    with pytest.raises(subprocess.CalledProcessError):
        probe("https://www.youtube.com/watch?v=abc123")


def test_probe_parses_a_successful_run(monkeypatch):
    install_fake(monkeypatch, 0, stdout="not_live\n743\n")
    assert probe("https://www.youtube.com/watch?v=abc123") == ("not_live", 743)
