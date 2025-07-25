# AsyncYT
![PyPI](https://img.shields.io/pypi/v/asyncyt?style=for-the-badge)
![Downloads](https://img.shields.io/pypi/dm/asyncyt?style=for-the-badge)
![License](https://img.shields.io/pypi/l/asyncyt?style=for-the-badge)

**AsyncYT** is a fully async, high-performance Any website downloader powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp) and `ffmpeg`.  
It comes with auto binary setup, progress tracking, playlist support, search, and clean API models using `pydantic`.

## ✨ Features

- ✅ Async from the ground up
- 🎵 Audio/video/playlist support
- 🌐 Auto-download `yt-dlp` and `ffmpeg`
- 🧠 Strongly typed config and models
- 📡 Live progress (WebSocket-friendly)
- 📚 Clean and extensible

## 📦 Install

```bash
pip install asyncyt
```

## 🚀 Example

```python
from asyncyt import Downloader, DownloadConfig, Quality

config = DownloadConfig(quality=Quality.HD_720P)
downloader = Downloader()

await downloader.setup_binaries()
info = await downloader.get_video_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
print(info.title)

filename = await downloader.download(info.url, config)
print("Downloaded to", filename)
```

## 📚 API Overview

| Method | Description |
| ------ | ----------- |
| `await setup_binaries()` | Download yt-dlp and ffmpeg if needed. |
| `await setup_binaries_generator()` | Same as above, but yields progress updates. |
| `await get_video_info(url)` | Get metadata for a video. |
| `await download(url, request, progress_callback)` | Download a video with progress updates. |
| `await download_with_response(request, url, progress_callback)` | Download with a detailed API-style response. |
| `await search(request)` | Search videos. |
| `await download_playlist(request, progress_callback)` | Download a playlist with progress updates. |
| `await health_check()` | Verify binaries. |

## 📖 Documentation

👉 [Read the Docs](https://github.com/mahirox36/AsyncYT/wiki)

## 📜 License

MIT © MahiroX36
