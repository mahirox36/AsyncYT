"""
13_api_response.py
----------------------------
Use download_with_response() for an API-friendly envelope that always
returns a structured object instead of raising exceptions.
Ideal for FastAPI / Flask endpoints or any service layer.
"""

import asyncio
import json
from asyncyt import AsyncYT
from asyncyt.basemodels import DownloadConfig, DownloadRequest
from asyncyt.enums import Quality, VideoFormat


async def handle_download(yt: AsyncYT, url: str) -> dict:
    """Simulate an API endpoint handler."""
    config = DownloadConfig(
        output_path="./downloads/api",
        quality=Quality.HD_720P,
        video_format=VideoFormat.MP4,
        embed_metadata=True,
    )

    request = DownloadRequest(url=url, config=config)
    response = await yt.download_with_response(request=request)

    # Convert to a dict safe for JSON serialisation
    return {
        "success": response.success,
        "message": response.message,
        "id": response.id,
        "filename": response.filename,
        "error": response.error,
        "video": {
            "title": response.video_info.title,
            "duration": response.video_info.duration,
            "uploader": response.video_info.uploader,
            "views": response.video_info.view_count,
        } if response.video_info else None,
    }


async def main():
    yt = AsyncYT()
    await yt.setup_binaries()

    # Good URL
    result = await handle_download(yt, "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    print("=== Response ===")
    print(json.dumps(result, indent=2))

    # Bad URL (shows error handling without exception)
    bad_result = await handle_download(yt, "https://www.youtube.com/watch?v=INVALID_URL")
    print("\n=== Bad URL Response ===")
    print(json.dumps(bad_result, indent=2))


asyncio.run(main())
