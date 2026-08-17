"""Audio to text, by shelling out to yt-dlp, ffmpeg and whisper.cpp."""

import subprocess
import time
from pathlib import Path


def download_audio(url, workdir, attempts=3, delay=30):
    # YouTube serves an occasional 403 for a video it will hand over happily a
    # minute later: the same URL, with this same command line, failed three
    # times running and then succeeded untouched. Without a retry one 403 costs
    # the whole video until the next nightly run, which then gets one attempt
    # of its own — videos were observed failing two nights in a row that way.
    for attempt in range(1, attempts + 1):
        try:
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
            return
        except subprocess.CalledProcessError:
            if attempt == attempts:
                raise
            time.sleep(delay)


def transcribe(url, whisper_bin, model, device, workdir):
    audio = Path(workdir) / "audio.opus"
    pcm = Path(workdir) / "pcm.wav"
    download_audio(url, workdir)
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
