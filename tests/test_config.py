# tests/test_config.py
import pytest
from asyncyt import DownloadConfig, AudioFormat

def test_valid_config():
    config = DownloadConfig(
        output_path="./downloads",
        audio_format=AudioFormat.MP3,
        extract_audio=True
    ) # type: ignore
    assert config.audio_format == AudioFormat.MP3.value

def test_invalid_rate_limit():
    with pytest.raises(ValueError):
        DownloadConfig(rate_limit="999X") # type: ignore
