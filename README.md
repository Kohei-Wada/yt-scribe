# yt-scribe

Turns YouTube channels into an Atom feed whose entries carry the transcript, so
any feed reader can treat a video as an ordinary article.

A video cannot be skimmed. A feed reader shows a title and a thumbnail and asks
you to spend twenty minutes finding out whether it was worth it. This produces
the text first, so you decide by reading.

It is not a reader. It emits a feed; subscribe to it from whatever you already
use.

## Why not an existing tool

- Karakeep crawls a YouTube link to its description and nothing more.
  [#1629](https://github.com/karakeep-app/karakeep/issues/1629) has asked for
  transcription since 2025-06.
- oksskolten extracts full text and summarises against a local model, but states
  it does not handle YouTube.
- RSSHub has a provider per source, but its routes answer HTTP requests and
  transcription takes far longer than a request should.
- YouTube's auto-captions are not a substitute: on one Japanese video they gave
  1,951 characters against whisper's 4,436, corrupted meaning, and rate-limited.

## Requirements

`yt-dlp`, `ffmpeg`, and `whisper-cli` from
[whisper.cpp](https://github.com/ggerganov/whisper.cpp) on PATH, plus a ggml
model. Python 3.11 or newer, and [uv](https://docs.astral.sh/uv/). No Python
dependencies at runtime — uv is here for the dev environment and the lockfile,
not because the code needs anything.

A GPU makes this fast rather than possible. On an RTX 5090 through whisper.cpp's
Vulkan backend, transcription runs at 63-66x realtime — an hour of video in
about a minute. On CPU expect roughly realtime and use a smaller model.

Summarisation is optional and talks to any OpenAI-compatible endpoint, so Ollama,
vLLM, llama.cpp or a hosted API all work.

## Use

```bash
git clone https://github.com/Kohei-Wada/yt-scribe && cd yt-scribe
uv sync
cp config.example.toml config.toml
$EDITOR config.toml          # channel ids, whisper model path, device
uv run yt-scribe --config config.toml
```

That writes `feed.xml`. Point a reader at it, either through a web server you
already run or with the built-in one:

```bash
uv run yt-scribe --config config.toml --serve 8110
```

Run it from a timer. Each run picks up new videos, transcribes at most `limit`
of them, and rewrites the feed. Videos shorter than `min_duration` seconds are
skipped without being transcribed, which keeps shorts out of the feed; it is off
by default, and 180 is YouTube's upper bound for a short.

On NixOS, and anywhere else the system CA bundle is not where Python expects it,
uv's own interpreter cannot verify TLS and every channel fetch fails with
`CERTIFICATE_VERIFY_FAILED`. Point it at the bundle:

```bash
SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt uv run yt-scribe --config config.toml
```

## Development

`make help` lists everything. The tests need no external binaries and no
network, so the whole check runs anywhere:

```bash
make install    # uv sync --dev
make hooks      # pre-commit, including the commit-message linter
make check      # lint, typecheck, test — the same three CI runs
```

CI runs those on every push and pull request, and the test job runs on 3.11 and
3.13 because 3.11 is the floor `tomllib` sets.

## Configuration

See `config.example.toml`. Two settings are worth reading twice:

`whisper.device` is not auto-detected. Machines often enumerate an integrated
GPU first, and choosing it is not an error — just far slower. On the machine
this was written for, device 0 is the integrated GPU and device 1 is the
discrete card: 97 seconds against 4.4 on the same clip. `whisper-cli -h` prints
the list.

Deleting the whole `[summary]` section stores transcripts without summaries.

## Behaviour worth knowing

Live and upcoming streams are skipped and left unrecorded, so they are picked up
once they become ordinary recordings.

A video that fails is logged and left unrecorded, so the next run retries it.
The process exits non-zero only when there was work and none of it succeeded.

Entry content is the summary first, then the transcript with whisper's own
timestamps. Readers show the summary in a list view; search reaches the whole
transcript; the timestamps let you find the moment in the video by eye.
