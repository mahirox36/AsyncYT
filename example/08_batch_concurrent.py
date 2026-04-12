"""
08_batch_concurrent.py
--------------------------------
Download multiple videos concurrently using asyncio.gather().
Each download gets its own progress callback identified by URL.

Set MAX_CONCURRENT to limit how many downloads run at once,
which avoids hammering the network or running out of disk space.
"""

import asyncio
from asyncyt import AsyncYT
from asyncyt.basemodels import DownloadConfig, DownloadProgress
from asyncyt.encoding import EncodingConfig, VideoEncodingConfig, AudioEncodingConfig
from asyncyt.enums import Quality, VideoFormat, VideoCodec, AudioCodec, Preset, PixelFormat

URLS = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/watch?v=9bZkp7q19f0",
    "https://www.youtube.com/watch?v=JGwWNGJdvx8",
]

MAX_CONCURRENT = 2   # download 2 at a time


def make_progress_callback(label: str):
    def on_progress(p: DownloadProgress):
        if p.status == "downloading":
            print(f"  [{label}] ⬇  {p.percentage:.1f}%  {p.speed}")
        elif p.status == "encoding":
            print(f"  [{label}] 🎬 Encoding {p.encoding_percentage:.1f}%  {p.encoding_bitrate}  speed={p.encoding_speed}")
        elif p.status == "completed":
            print(f"  [{label}] ✅ Complete!")
    return on_progress


async def download_one(yt: AsyncYT, url: str, semaphore: asyncio.Semaphore):
    label = url.split("v=")[-1][:8]
    config = DownloadConfig(
        output_path="./downloads/batch",
        quality=Quality.HD_720P,
        video_format=VideoFormat.MP4,
        embed_metadata=True,
        encoding=EncodingConfig(
            video=VideoEncodingConfig(
                codec=VideoCodec.H264,
                crf=23,
                preset=Preset.FAST,    # faster preset for batch jobs
                pixel_format=PixelFormat.YUV420P,
            ),
            audio=AudioEncodingConfig(
                codec=AudioCodec.AAC,
                bitrate="128k",
            ),
        ),
    )
    async with semaphore:
        print(f"\n▶  Starting [{label}]")
        try:
            path = await yt.download(url, config, make_progress_callback(label))
            print(f"  [{label}] 📁 {path}")
            return path
        except Exception as e:
            print(f"  [{label}] ❌ Failed: {e}")
            return None


async def main():
    yt = AsyncYT()
    await yt.setup_binaries()

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    tasks = [download_one(yt, url, semaphore) for url in URLS]
    results = await asyncio.gather(*tasks)

    print("\n\n=== Summary ===")
    for url, result in zip(URLS, results):
        status = result or "FAILED"
        print(f"  {url.split('v=')[-1]}: {status}")


asyncio.run(main())
