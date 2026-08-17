import subprocess

import pytest

from yt_scribe import transcribe as transcribe_module
from yt_scribe.transcribe import download_audio

FORBIDDEN = "ERROR: unable to download video data: HTTP Error 403: Forbidden\n"


def install_fake(monkeypatch, returncodes):
    """Fake yt-dlp that returns each code in turn, and records its calls."""
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        code = returncodes[len(calls) - 1]
        if code != 0:
            raise subprocess.CalledProcessError(code, cmd, "", FORBIDDEN)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(transcribe_module.subprocess, "run", fake_run)
    monkeypatch.setattr(transcribe_module.time, "sleep", lambda _: None)
    return calls


def test_a_transient_403_is_retried(monkeypatch, tmp_path):
    # YouTube hands out a 403 for a video it will serve happily a moment later;
    # observed on the same video succeeding on a later attempt with an
    # unchanged command line.
    calls = install_fake(monkeypatch, [1, 0])
    download_audio("https://www.youtube.com/watch?v=abc123", tmp_path)
    assert len(calls) == 2


def test_a_successful_download_is_not_repeated(monkeypatch, tmp_path):
    calls = install_fake(monkeypatch, [0])
    download_audio("https://www.youtube.com/watch?v=abc123", tmp_path)
    assert len(calls) == 1


def test_the_last_attempt_raises(monkeypatch, tmp_path):
    # A video that is genuinely unavailable must still fail, so the caller
    # counts it and moves on rather than the run hanging on it.
    calls = install_fake(monkeypatch, [1, 1, 1])
    with pytest.raises(subprocess.CalledProcessError):
        download_audio("https://www.youtube.com/watch?v=abc123", tmp_path, attempts=3)
    assert len(calls) == 3
