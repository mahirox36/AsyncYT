"""
07_fast_remux.py
--------------------------
Just remux streams into a different container — no re-encoding.
This is nearly instantaneous and preserves 100% of quality.

Use this when:
- You already have the video in a good codec (e.g. VP9/AV1 from YouTube)
- You just want to change the container (WebM → MKV)
- You don't want to lose any quality or spend CPU time

No EncodingConfig needed — just set video_format and leave encoding=None.
yt-dlp will use --remux-video automatically.
"""

import asyncio
from asyncyt import AsyncYT
from asyncyt.basemodels import DownloadConfig, DownloadProgress
from asyncyt.enums import Quality, VideoFormat


async def on_progress(p: DownloadProgress):
    match p.status:
        case "downloading":
            print(f"\r⬇  {p.percentage:.1f}%  {p.speed}", end="", flush=True)
        case "merging":
            print("\n🔀 Merging video + audio streams …")
        case "remuxing":
            print("📦 Remuxing container …")
        case "completed":
            print("✅ Done — zero quality loss!")


async def main():
    yt = AsyncYT()
    await yt.setup_binaries()

    config = DownloadConfig(
        output_path="./downloads/remux",
        quality=Quality.HD_1080P,
        video_format=VideoFormat.MKV,   # just change container, no re-encode
        embed_metadata=True,
        embed_thumbnail=True,
        # encoding=None  ← default, triggers --remux-video instead of --recode-video
    )

    path = await yt.download(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        config,
        on_progress,
    )
    print(f"\nSaved: {path}")


asyncio.run(main())
