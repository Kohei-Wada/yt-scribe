"""Audio to text, by shelling out to yt-dlp, ffmpeg and whisper.cpp."""

import subprocess
from pathlib import Path


def transcribe(url, whisper_bin, model, device, workdir):
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
