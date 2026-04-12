"""
04_4k_hevc_nvenc.py
-----------------------------
Download 4K and re-encode with NVIDIA hardware HEVC (hevc_nvenc).
Falls back to software libx265 if NVENC is unavailable.

Hardware presets for NVENC differ from software x265:
  p1 = fastest, p7 = slowest/best (NVENC-specific preset names)
  OR you can still pass "fast", "medium", "slow" — NVENC maps them.

CRF equivalent for NVENC is -cq (constant quality) passed via extra_args.
"""

import asyncio
from asyncyt import AsyncYT
from asyncyt.basemodels import DownloadConfig, DownloadProgress
from asyncyt.encoding import EncodingConfig, VideoEncodingConfig, AudioEncodingConfig
from asyncyt.enums import (
    Quality, VideoFormat, VideoCodec, AudioCodec,
    Preset, PixelFormat,
)


async def on_progress(p: DownloadProgress):
    if p.status == "encoding":
        print(
            f"\r🎮 GPU Encoding {p.encoding_percentage:.1f}%"
            f" | fps={p.encoding_fps}"
            f" | speed={p.encoding_speed}"
            f" | {p.encoding_bitrate}",
            end="",
            flush=True,
        )
    elif p.status == "downloading":
        print(f"\r⬇  {p.percentage:.1f}%  {p.speed}", end="", flush=True)
    elif p.status == "completed":
        print("\n✅ Done!")


async def main():
    yt = AsyncYT()
    await yt.setup_binaries()

    config = DownloadConfig(
        output_path="./downloads/4k",
        quality=Quality.UHD_4K,
        video_format=VideoFormat.MKV,
        embed_metadata=True,
        encoding=EncodingConfig(
            video=VideoEncodingConfig(
                codec=VideoCodec.HEVC_NVENC,      # NVIDIA GPU encode
                preset=Preset.SLOW,               # NVENC maps this to p6
                pixel_format=PixelFormat.YUV420P,
                # NVENC uses -cq instead of -crf for constant quality mode
                extra_args=["-cq", "24", "-rc", "vbr", "-b:v", "0"],
            ),
            audio=AudioEncodingConfig(
                codec=AudioCodec.OPUS,
                bitrate="256k",
            ),
        ),
    )

    path = await yt.download(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        config,
        on_progress,
    )
    print(f"\nSaved: {path}")


asyncio.run(main())
