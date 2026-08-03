import pytest

from yt_scribe.config import load

MINIMAL = """
channels = ["UCabc"]
[whisper]
model = "/m.bin"
"""

WITH_SUMMARY = (
    MINIMAL
    + """
[summary]
endpoint = "http://x/v1"
model = "m"
prompt = "p"
"""
)


def write(tmp_path, text):
    path = tmp_path / "c.toml"
    path.write_text(text)
    return path


def test_defaults_are_applied(tmp_path):
    config = load(write(tmp_path, MINIMAL))
    assert config.channels == ("UCabc",)
    assert config.whisper_bin == "whisper-cli"
    assert config.whisper_device == "0"
    assert config.limit == 20
    assert config.min_duration == 0
    assert config.summary is None


def test_summary_section_is_read(tmp_path):
    config = load(write(tmp_path, WITH_SUMMARY))
    assert config.summary.endpoint == "http://x/v1"
    assert config.summary.api_key is None


def test_channels_are_required(tmp_path):
    with pytest.raises(ValueError, match="channels"):
        load(write(tmp_path, '[whisper]\nmodel = "/m.bin"\n'))


def test_whisper_model_is_required(tmp_path):
    with pytest.raises(ValueError, match=r"whisper\.model"):
        load(write(tmp_path, 'channels = ["UCabc"]\n'))


@pytest.mark.parametrize("missing", ["endpoint", "model", "prompt"])
def test_summary_keys_are_required(tmp_path, missing):
    keys = {"endpoint": '"http://x/v1"', "model": '"m"', "prompt": '"p"'}
    del keys[missing]
    section = "\n".join(f"{k} = {v}" for k, v in keys.items())
    with pytest.raises(ValueError, match=f"summary.{missing}"):
        load(write(tmp_path, MINIMAL + "[summary]\n" + section + "\n"))


def test_min_duration_is_read(tmp_path):
    config = load(
        write(
            tmp_path,
            'channels = ["UCabc"]\nmin_duration = 180\n[whisper]\nmodel = "/m.bin"\n',
        )
    )
    assert config.min_duration == 180
