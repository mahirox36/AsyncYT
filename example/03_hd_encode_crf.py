"""
03_hd_encode_crf.py
-----------------------------
Download 1080p, re-encode to H.264 CRF 20 (high quality, smaller file)
with AAC audio, embedded thumbnail and subtitles.

CRF (Constant Rate Factor):
  0  = lossless
  18 = visually lossless (for most content)
  20 = excellent quality  ← good default
  23 = default x264 quality
  28 = noticeably compressed
  51 = worst
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
    match p.status:
        case "downloading":
            print(f"  ⬇  {p.percentage:5.1f}%  {p.speed:>12}  ETA {p.eta}s")
        case "merging":
            print("  🔀  Merging streams …")
        case "encoding":
            print(
                f"  🎬  Encoding {p.encoding_percentage:5.1f}%"
                f"  frame={p.encoding_frame}"
                f"  fps={p.encoding_fps}"
                f"  {p.encoding_bitrate}"
                f"  speed={p.encoding_speed}"
                f"  size={p.encoding_size}"
                f" eta={p.encoding_percentage}%"
            )
        case "completed":
            print("  ✅  Done!")


async def main():
    yt = AsyncYT()
    await yt.setup_binaries()

    config = DownloadConfig(
        output_path="./downloads/hd",
        quality=Quality.HD_1080P,
        video_format=VideoFormat.MP4,
        embed_thumbnail=True,
        embed_metadata=True,
        embed_subs=True,
        subtitle_lang="en",
        encoding=EncodingConfig(
            video=VideoEncodingConfig(
                codec=VideoCodec.H264,
                crf=20,                          # high quality
                preset=Preset.SLOW,              # slower = better compression
                tune=TuneOption.FILM,            # optimised for live-action
                pixel_format=PixelFormat.YUV420P,  # max compat (required for some players)
            ),
            audio=AudioEncodingConfig(
                codec=AudioCodec.AAC,
                bitrate="192k",
                sample_rate=48000,
            ),
            overwrite=False,
        ),
    )

    print("Starting 1080p H.264 CRF-20 download …\n")
    path = await yt.download(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        config,
        on_progress,
    )
    print(f"\nFile: {path}")


asyncio.run(main())
