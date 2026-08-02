"""Audio to text, by shelling out to yt-dlp, ffmpeg and whisper.cpp."""

import subprocess
from pathlib import Path

SKIP_STATUSES = ("is_live", "is_upcoming")


def live_status(output: str) -> str:
    lines = [line for line in output.strip().splitlines() if line.strip()]
    return lines[-1].strip() if lines else "unknown"


def transcribe(url, whisper_bin, model, device, workdir):
    # A live stream never finishes downloading, so it would consume the whole
    # download timeout and starve everything behind it. Ask first; this is a
    # metadata call of about two seconds.
    probe = subprocess.run(
        ["yt-dlp", "--no-warnings", "--print", "%(live_status)s", "--", url],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    # None, not "": a stream becomes an ordinary recording once it ends, so it
    # is left unrecorded to be picked up later rather than written off.
    if live_status(probe.stdout) in SKIP_STATUSES:
        return None

    audio = Path(workdir) / "audio.opus"
    pcm = Path(workdir) / "pcm.wav"
    subprocess.run(
        [
            "yt-dlp",
            "-q",
            "--no-warnings",
            "-x",
            "--audio-format",
            "opus",
            "-o",
            Path(workdir) / "audio.%(ext)s",
            "--",
            url,
        ],
        check=True,
        timeout=1800,
    )
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            audio,
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            pcm,
        ],
        check=True,
        timeout=1800,
    )
    # -l auto is load-bearing: whisper-cli defaults to English rather than
    # detecting, and mangles other languages silently instead of failing.
    # whisper writes the transcript to stdout and its progress to stderr, so
    # capturing stdout alone gives the transcript and nothing else.
    result = subprocess.run(
        [whisper_bin, "-m", model, "-f", pcm, "-dev", device, "-l", "auto"],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
        timeout=3600,
    )
    return result.stdout.strip()
