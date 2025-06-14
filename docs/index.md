Welcome to the documentation for **AsyncYT** 🧠✨  
A YouTube downloader that’s cute, clean, and async from top to bottom!

## 💻 Modules

### Downloader

```py
from asyncyt import Downloader
```

Main class with:

- `get_video_info(url)`
- `download(url, config)`
- `search(query)`
- and more!

### Configuration

```py
DownloadConfig(...)
```

Config options for:

- Quality
- Audio/Video formats
- Subtitles
- Output path
- Retry settings

## ✨ Powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [FFmpeg](https://ffmpeg.org/)
