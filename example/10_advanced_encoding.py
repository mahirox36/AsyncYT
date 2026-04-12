"""
10_advanced_encoding.py
---------------------------------
Advanced encoding: target bitrate + VBV buffer (for streaming),
downscale to 720p, force 30fps, tune for animation.

VBV (Video Buffer Verifier) ensures the bitrate never spikes above
-maxrate, which is critical for streaming / upload to platforms with
strict bitrate limits (e.g. Twitch, YouTube, Discord).

Useful settings reference:
  -b:v 2M          → target 2 Mbit/s average video bitrate
  -maxrate 3M       → never exceed 3 Mbit/s
  -bufsize 6M       → VBV buffer = 2× maxrate is a common recommendation
  -vf scale=1280:720 → downscale to 720p, keeping exact resolution
  -r 30             → lock to 30 fps (drops or duplicates frames as needed)
  -tune animation   → optimise for animated content
"""

import asyncio
from asyncyt import AsyncYT
from asyncyt.basemodels import DownloadConfig, DownloadProgress
from asyncyt.encoding import EncodingConfig, VideoEncodingConfig, AudioEncodingConfig
from asyncyt.enums import (
    Quality, VideoFormat, VideoCodec, AudioCodec,
    Preset, PixelFormat, TuneOption,
)


async def on_progress(p: DownloadProgress):
    if p.status == "encoding":
        print(
            f"  🎬 {p.encoding_percentage:5.1f}%"
            f"  frame={p.encoding_frame:<6}"
            f"  fps={str(p.encoding_fps):<6}"
            f"  {str(p.encoding_bitrate):<18}"
            f"  speed={p.encoding_speed}"
            f"  size={p.encoding_size}"
            f"  time={p.encoding_time}"
        )
    elif p.status == "downloading":
        print(f"  ⬇  {p.percentage:.1f}%  {p.speed}  ETA {p.eta}s")
    elif p.status in ("merging", "remuxing"):
        print(f"  🔀 {p.status.capitalize()} …")
    elif p.status == "completed":
        print("  ✅ All done!")


async def main():
    yt = AsyncYT()
    await yt.setup_binaries()

    config = DownloadConfig(
        output_path="./downloads/advanced",
        quality=Quality.HD_1080P,     # download source in 1080p
        video_format=VideoFormat.MP4,
        embed_metadata=True,
        embed_thumbnail=True,
        embed_subs=True,
        subtitle_lang="en",
        encoding=EncodingConfig(
            video=VideoEncodingConfig(
                codec=VideoCodec.H264,
                # CBR-like mode with VBV for controlled streaming quality
                bitrate="2M",
                maxrate="3M",
                bufsize="6M",
                preset=Preset.MEDIUM,
                tune=TuneOption.ANIMATION,
                pixel_format=PixelFormat.YUV420P,
                # Downscale to exactly 720p and lock to 30fps
                width=1280,
                height=720,
                fps=30,
                extra_args=[
                    "-profile:v", "high",  # H.264 High profile
                    "-level", "4.1",       # required for some devices / platforms
                ],
            ),
            audio=AudioEncodingConfig(
                codec=AudioCodec.AAC,
                bitrate="192k",
                sample_rate=48000,
                # extra AAC-specific: use the newer FDK encoder if available
                # extra_args=["-strict", "experimental"],
            ),
            overwrite=True,
            extra_global_args=["-threads", "0"],  # 0 = auto-detect CPU count
        ),
    )

    print("Advanced VBV-controlled encode to 720p30 …\n")
    path = await yt.download(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        config,
        on_progress,
    )
    print(f"\nSaved: {path}")


asyncio.run(main())
