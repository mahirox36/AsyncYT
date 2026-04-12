"""
01_simple_download.py
------------------------------
The most basic usage — download a video with default settings.
No encoding config needed; yt-dlp picks the best available quality
and remuxes to the original container.
"""

import asyncio
from asyncyt import AsyncYT, VideoFormat
from asyncyt.basemodels import DownloadConfig, DownloadProgress

# function to handle progress updates
async def on_progress(p: DownloadProgress):
    print(f"[{p.status.upper()}] {p.percentage:.1f}%  speed={p.speed}  eta={p.eta}s")


async def main():
    yt = AsyncYT()
    await yt.setup_binaries()  # downloads yt-dlp + ffmpeg if not already present
    
    config = DownloadConfig(
        output_path="./downloads",
        embed_thumbnail=True,
        embed_metadata=True,
        video_format=VideoFormat.MP4,
        embed_subs=True,
    )

    path = await yt.download(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        config,
        on_progress,
    )
    print(f"\nSaved to: {path}")


asyncio.run(main())
