# Installation

AsyncYT requires Python 3.10+ and works on Windows, macOS, and Linux.

## 1. Install via pip

```sh
pip install asyncyt
```

## 2. Install system dependencies

- **ffmpeg**: Required for audio/video processing.
  - Windows: AsyncYT can auto-download ffmpeg.
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg`

- **yt-dlp**: AsyncYT will auto-download yt-dlp binary if not found.

## 3. (Optional) Update binaries

To force re-download of yt-dlp/ffmpeg, delete the `bin/` folder in your project root.

---

Next: [Usage](./usage.md)
