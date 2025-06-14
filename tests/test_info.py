# tests/test_info.py
import pytest

@pytest.mark.asyncio
async def test_get_video_info(downloader):
    downloader = await downloader
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    info = await downloader.get_video_info(url)

    assert info.title
    assert info.duration > 0
    assert info.uploader.lower() == "rickastleyvevo"
