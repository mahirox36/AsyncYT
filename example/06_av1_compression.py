"""
06_av1_compression.py
-------------------------------
Download and re-encode to AV1 (libaom-av1) for maximum compression.
AV1 at CRF 30 can be ~50% smaller than H.264 at equivalent quality.

⚠️  Software AV1 (libaom-av1) is VERY slow.
    For faster encoding use libsvtav1 or av1_nvenc (Nvidia RTX 30xx+).

AV1 CRF range: 0 (lossless) → 63 (worst)
Typical good values: 23–35
"""

import asyncio
from asyncyt import AsyncYT
from asyncyt.basemodels import DownloadConfig, DownloadProgress
from asyncyt.encoding import EncodingConfig, VideoEncodingConfig, AudioEncodingConfig
from asyncyt.enums import (
    Quality, VideoFormat, VideoCodec, AudioCodec,
    PixelFormat,
)


async def on_progress(p: DownloadProgress):
    if p.status == "encoding":
        # AV1 is slow, so show lots of detail
        print(
            f"\r🌿 AV1 {p.encoding_percentage:.1f}%"
            f" | frame {p.encoding_frame}"
            f" | {p.encoding_fps} fps"
            f" | {p.encoding_bitrate}"
            f" | speed {p.encoding_speed}"
            f" | {p.encoding_size}",
            end="",
            flush=True,
        )
    elif p.status == "downloading":
        print(f"\r⬇  {p.percentage:.1f}%  {p.speed}", end="", flush=True)
    elif p.status == "completed":
        print("\n✅ AV1 encode complete!")


async def main():
    yt = AsyncYT()
    await yt.setup_binaries()

    config = DownloadConfig(
        output_path="./downloads/av1",
        quality=Quality.HD_1080P,
        video_format=VideoFormat.MKV,
        embed_metadata=True,
        encoding=EncodingConfig(
            video=VideoEncodingConfig(
                codec=VideoCodec.AV1,
                crf=30,
                pixel_format=PixelFormat.YUV420P,
                # libaom-av1 specific: cpu-used controls speed vs quality
                # 0=slowest/best, 8=fastest/worst  (default 1)
                extra_args=["-cpu-used", "4", "-row-mt", "1"],
            ),
            audio=AudioEncodingConfig(
                codec=AudioCodec.OPUS,     # OPUS pairs naturally with AV1 in MKV
                bitrate="128k",
            ),
        ),
    )

    print("Starting AV1 encode (this will be slow on CPU)…\n")
    path = await yt.download(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        config,
        on_progress,
    )
    print(f"\nSaved: {path}")


asyncio.run(main())
