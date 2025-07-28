# AsyncYT

![PyPI - Version](https://img.shields.io/pypi/v/asyncyt?style=for-the-badge)
![Downloads](https://img.shields.io/pypi/dm/asyncyt?style=for-the-badge)
![License](https://img.shields.io/pypi/l/asyncyt?style=for-the-badge)

**AsyncYT** is a fully async, high-performance media downloader for 1000+ websites powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp) and `ffmpeg`.  
It comes with auto binary setup, progress tracking, playlist support, search, and clean API models using `pydantic`.

## ✨ Features

- ✅ **Fully Async Architecture** – every operation is non‑blocking and `await`‑ready.
- 🎥 **Video, Audio, and Playlist Support** – download any media you throw at it.
- 🌐 **Automatic Tool Management** – will grab `yt-dlp` and `ffmpeg` for you if not installed.
- 🎛 **Advanced FFmpeg Configuration** – control codecs, bitrates, CRF, presets, and more via strongly‑typed enums.
- 📡 **Real‑Time Progress Tracking** – both download and FFmpeg processing progress, perfect for UI updates or WebSockets.
- 🧩 **Standalone AsyncFFmpeg** – use the FFmpeg engine by itself for your own media workflows (no downloading required).
- 🔍 **Media Inspection** – get detailed file info (resolution, duration, codecs, etc.) through `AsyncFFmpeg.get_file_info()`.
- ⚙️ **Asynchronous FFmpeg Processing** – run FFmpeg jobs with `AsyncFFmpeg.process()` without blocking your app.
- 🎬 **Video & Audio Codec Enums** – pick codecs safely with built‑in enums.
- ⚡ **Presets for Performance** – quickly switch between `ultrafast`, `fast`, `medium`, and more with type‑safe presets.
- 📚 **Inline Documentation** – every public method is documented and typed for easy discoverability.
- 🔗 **Codec Compatibility Helpers** – utilities to check which formats and codecs pair nicely.

## 📋 Requirements

- Python 3.11+
- Cross-platform – Windows, macOS, Linux
- Dependencies: pydantic (auto-installed)
- Optional: yt-dlp and ffmpeg (auto-downloaded if not present)

## 📦 Install

```bash
pip install asyncyt
```

## 🚀 Quick Start

```py
import asyncio
from asyncyt import AsyncYT, DownloadConfig, Quality

async def main():
    config = DownloadConfig(quality=Quality.HD_720P)
    downloader = AsyncYT()

    try:
        await downloader.setup_binaries()
        info = await downloader.get_video_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        print(f"Downloading: {info.title}")
        filename = await downloader.download(info.url, config)
        print(f"Downloaded to: {filename}")
    except AsyncYTBase as e: # AsyncYTBase is the base for all exceptions in this library"
        print(f"Error: {e}")

asyncio.run(main())
```

## 🌐 Supported Sites

AsyncYT supports **1000+ websites** through yt-dlp, including:

- YouTube, YouTube Music
- Twitch, TikTok, Instagram
- Twitter, Reddit, Facebook
- Vimeo, Dailymotion, and many more

[See full list of supported sites →](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

## 📖 Documentation

👉 [Read the Docs](https://github.com/mahirox36/AsyncYT/wiki)

## 🤝 Contributing

Contributions are welcome! Feel free to open an issue or pull request.

## 📜 License

MIT © **MahiroX36**
