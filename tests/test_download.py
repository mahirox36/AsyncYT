# tests/test_download.py
import pytest
from asyncyt import DownloadConfig, Quality, VideoFormat

@pytest.mark.asyncio
async def test_download_video(downloader):
    downloader = await downloader
    config = DownloadConfig(quality=Quality.BEST, video_format=VideoFormat.MP4) # type: ignore
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    filename = await downloader.download(url, config)
    assert filename.endswith(".mp4")
