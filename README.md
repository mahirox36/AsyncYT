# AsyncYT

**AsyncYT** is a fully async, high-performance Any website downloader powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp) and `ffmpeg`.  
It comes with auto binary setup, progress tracking, playlist support, search, and clean API models using `pydantic`.

## Features

- ✅ Async from the ground up
- 🎵 Audio/video/playlist support
- 🌐 Auto-download `yt-dlp` and `ffmpeg`
- 🧠 Strongly typed config and models
- 📡 Live progress (WebSocket-friendly)
- 📚 Clean and extensible

## Install

```bash
pip install asyncyt
```

## Example

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

## Documentation

👉 [Read the Docs](https://mahirox36.github.io/AsyncYT)

## License

MIT © MahiroX36
