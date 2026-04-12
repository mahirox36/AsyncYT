"""
05_flac_lossless.py
-----------------------------
Extract audio as 24-bit FLAC (lossless).
Great for archiving music or podcasts at full quality.

FLAC quality levels:
  0 = fastest compression
  8 = best compression (still lossless, just slower to encode)
  Default is 5.
"""

import asyncio
from asyncyt import AsyncYT
from asyncyt.basemodels import DownloadConfig, DownloadProgress
from asyncyt.encoding import EncodingConfig, AudioEncodingConfig
from asyncyt.enums import AudioFormat, AudioCodec, AudioChannels, Quality


async def on_progress(p: DownloadProgress):
    if p.status == "downloading":
        print(f"\r⬇  {p.percentage:.1f}%  {p.speed}", end="", flush=True)
    elif p.status == "encoding":
        print(f"\r🎵 Encoding FLAC {p.encoding_percentage:.1f}%", end="", flush=True)
    elif p.status == "completed":
        print("\n✅ Lossless FLAC saved!")


async def main():
    yt = AsyncYT()
    await yt.setup_binaries()

    config = DownloadConfig(
        output_path="./downloads/lossless",
        quality=Quality.AUDIO_ONLY,
        extract_audio=True,
        audio_format=AudioFormat.FLAC,
        embed_thumbnail=True,
        embed_metadata=True,
        encoding=EncodingConfig(
            audio=AudioEncodingConfig(
                codec=AudioCodec.FLAC,
                sample_rate=48000,
                channels=AudioChannels.STEREO,
                # FLAC compression level via extra_args (0=fast, 8=best compression)
                extra_args=["-compression_level", "8"],
            )
        ),
    )

    path = await yt.download(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        config,
        on_progress,
    )
    print(f"Saved: {path}")


asyncio.run(main())
