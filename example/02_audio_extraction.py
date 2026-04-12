"""
02_audio_extraction.py
--------------------------------
Extract audio only and save as MP3 with a specific bitrate.
Demonstrates AudioEncodingConfig and the ENCODING status callback.
"""

import asyncio
from asyncyt import AsyncYT
from asyncyt.basemodels import DownloadConfig, DownloadProgress
from asyncyt.encoding import EncodingConfig, AudioEncodingConfig
from asyncyt.enums import AudioFormat, AudioCodec, Quality


async def on_progress(p: DownloadProgress):
    if p.status == "downloading":
        bar = "#" * int(p.percentage / 5) + "-" * (20 - int(p.percentage / 5))
        print(f"\r[{bar}] {p.percentage:.1f}%  {p.speed}", end="", flush=True)

    elif p.status == "encoding":
        print(
            f"\r[ENCODING] {p.encoding_percentage:.1f}%"
            f"  fps={p.encoding_fps}"
            f"  bitrate={p.encoding_bitrate}"
            f"  speed={p.encoding_speed}",
            end="",
            flush=True,
        )

    elif p.status == "completed":
        print("\n[DONE]")


async def main():
    yt = AsyncYT()
    await yt.setup_binaries()

    config = DownloadConfig(
        output_path="./downloads/audio",
        quality=Quality.AUDIO_ONLY,
        extract_audio=True,
        audio_format=AudioFormat.MP3,
        embed_thumbnail=True,
        embed_metadata=True,
        encoding=EncodingConfig(
            audio=AudioEncodingConfig(
                codec=AudioCodec.MP3,
                bitrate="320k",   # CBR 320 kbps
                sample_rate=44100,
            )
        ),
    )

    path = await yt.download(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        config,
        on_progress,
    )
    print(f"Saved to: {path}")


asyncio.run(main())
