# AsyncYT

![PyPI - Version](https://img.shields.io/pypi/v/asyncyt?style=for-the-badge)
![Downloads](https://img.shields.io/pypi/dm/asyncyt?style=for-the-badge)
![License](https://img.shields.io/pypi/l/asyncyt?style=for-the-badge)

**AsyncYT** is a fully async, high-performance media downloader for 1000+ websites powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp) and `ffmpeg`.  
It comes with auto binary setup, progress tracking, playlist support, search, and clean API models using `pydantic`.

---

## ✨ Features

- ✅ **Fully Async Architecture** – every operation is non‑blocking and `await`‑ready.
- 🎥 **Video, Audio, and Playlist Support** – download any media you throw at it.
- 🌐 **Automatic Binary Management** – downloads `yt-dlp` and `ffmpeg` automatically if not found, with update support and resume-capable downloads.
- 🎛 **Rich FFmpeg Encoding Configuration** – control video/audio codecs, CRF, bitrates, presets, pixel formats, scale, FPS, VBV, and more via the new `EncodingConfig` model — translated directly into yt-dlp `--postprocessor-args` flags, no separate FFmpeg process needed.
- 📡 **Real‑Time Progress Tracking** – granular download _and_ FFmpeg encoding progress (percentage, FPS, speed multiplier, bitrate, frame count, elapsed time), perfect for UI updates or WebSockets.
- 🔀 **Smart Postprocessor Routing** – encoding args are automatically routed to the right yt-dlp postprocessor (`VideoConvertor`, `ExtractAudio`, `Merger`, `VideoRemuxer`) depending on your config.
- 🔁 **Resilient Downloads** – configurable retries, fragment retries, rate limiting, proxy support, cookies, and resume-capable binary downloads with exponential back-off.
- 🔍 **Video & Playlist Info** – retrieve full metadata (title, duration, uploader, view/like count, formats, thumbnail) before downloading.
- 🔎 **Built-in Search** – search YouTube directly and get back typed `VideoInfo` results.
- 🛡 **Strongly Typed Models** – every input and output is a validated `pydantic` model with schema extras and field-level docs.
- 📚 **Rich Enum Library** – type-safe enums for qualities, codecs, presets, pixel formats, audio channels, subtitle formats, progress statuses, and more.
- 🧩 **Clean Exception Hierarchy** – specific exceptions for every failure mode (download canceled, already exists, not found, yt-dlp errors, etc.).
- 🔗 **URL Cleaning Utilities** – normalises YouTube watch, `youtu.be`, `/shorts/`, and `/embed/` URLs automatically.
- 📂 **Safe File Management** – unique filename generation, overwrite control, and atomic temp-dir → output-dir moves.
- 🖥 **Cross-Platform** – Windows, macOS, and Linux; correct binaries are selected per platform automatically.

---

## 📋 Requirements

- Python 3.11+
- Cross-platform – Windows, macOS, Linux
- Optional: `yt-dlp` and `ffmpeg` (auto-downloaded if not present)

---

## 📦 Install

```bash
pip install asyncyt
```

---

## 🚀 Quick Start

```python
import asyncio
from asyncyt import AsyncYT, DownloadConfig, Quality
from asyncyt.exceptions import AsyncYTBase

async def main():
    downloader = AsyncYT()
    await downloader.setup_binaries()

    config = DownloadConfig(quality=Quality.HD_720P)

    info = await downloader.get_video_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    print(f"Downloading: {info.title}")

    filename = await downloader.download(info.url, config)
    print(f"Downloaded to: {filename}")

asyncio.run(main())
```

For more examples check the [Examples](/example/) folder.

---

## 🎛 Encoding Configuration

AsyncYT exposes a rich `EncodingConfig` model that gives you full control over how FFmpeg processes your media. It maps directly onto yt-dlp's `--postprocessor-args` / `--ppa` flags — no extra FFmpeg invocations.

```python
from asyncyt import AsyncYT, DownloadConfig, Quality, VideoFormat
from asyncyt.encoding import EncodingConfig, VideoEncodingConfig, AudioEncodingConfig
from asyncyt.enums import VideoCodec, AudioCodec, Preset, PixelFormat

config = DownloadConfig(
    quality=Quality.HD_1080P,
    video_format=VideoFormat.MP4,
    embed_metadata=True,
    embed_thumbnail=True,
    encoding=EncodingConfig(
        video=VideoEncodingConfig(
            codec=VideoCodec.H264,
            crf=20,
            preset=Preset.SLOW,
            pixel_format=PixelFormat.YUV420P,
        ),
        audio=AudioEncodingConfig(
            codec=AudioCodec.AAC,
            bitrate="192k",
        ),
        overwrite=True,
    ),
)
```

### VideoEncodingConfig options

| Field          | Type           | Description                                                                 |
| -------------- | -------------- | --------------------------------------------------------------------------- |
| `codec`        | `VideoCodec`   | FFmpeg video codec (e.g. `libx264`, `hevc_nvenc`)                           |
| `crf`          | `int` (0–63)   | Constant Rate Factor — quality vs. size. Mutually exclusive with `bitrate`. |
| `bitrate`      | `str`          | Target video bitrate, e.g. `"2M"`, `"800k"`                                 |
| `maxrate`      | `str`          | Max bitrate cap for VBV, e.g. `"4M"`                                        |
| `bufsize`      | `str`          | VBV buffer size, e.g. `"8M"`                                                |
| `preset`       | `Preset`       | Encoding speed preset (`ultrafast` … `placebo`)                             |
| `tune`         | `TuneOption`   | x264/x265 tune (`film`, `animation`, `grain` …)                             |
| `pixel_format` | `PixelFormat`  | Output pixel format (`yuv420p`, `yuv420p10le` …)                            |
| `width`        | `int`          | Output width in pixels (aspect ratio preserved when height omitted)         |
| `height`       | `int`          | Output height in pixels (aspect ratio preserved when width omitted)         |
| `fps`          | `int \| float` | Force output frame rate                                                     |
| `extra_args`   | `List[str]`    | Raw FFmpeg video args appended verbatim                                     |

### AudioEncodingConfig options

| Field         | Type            | Description                                                |
| ------------- | --------------- | ---------------------------------------------------------- |
| `codec`       | `AudioCodec`    | FFmpeg audio codec (e.g. `aac`, `libmp3lame`, `libopus`)   |
| `bitrate`     | `str`           | Target audio bitrate, e.g. `"192k"`, `"320k"`              |
| `quality`     | `int` (0–10)    | VBR quality (codec-specific scale)                         |
| `sample_rate` | `int`           | Output sample rate in Hz, e.g. `44100`, `48000`            |
| `channels`    | `AudioChannels` | Output channel layout (`MONO`, `STEREO`, `SURROUND_5_1` …) |
| `extra_args`  | `List[str]`     | Raw FFmpeg audio args appended verbatim                    |

### EncodingConfig options

| Field               | Type                  | Description                                            |
| ------------------- | --------------------- | ------------------------------------------------------ |
| `video`             | `VideoEncodingConfig` | Video encoding settings                                |
| `audio`             | `AudioEncodingConfig` | Audio encoding settings                                |
| `overwrite`         | `bool`                | Pass `-y` to FFmpeg to overwrite existing output files |
| `extra_global_args` | `List[str]`           | Raw FFmpeg global args, e.g. `["-threads", "4"]`       |

---

## 📡 Progress Tracking

Pass any async or sync callable as `progress_callback` to receive live `DownloadProgress` updates:

```python
from asyncyt import AsyncYT, DownloadConfig
from asyncyt.basemodels import DownloadProgress
from asyncyt.enums import ProgressStatus

async def on_progress(p: DownloadProgress):
    if p.status == ProgressStatus.DOWNLOADING:
        print(f"[Download] {p.percentage:.1f}%  {p.speed}  ETA {p.eta}s")
    elif p.status == ProgressStatus.ENCODING:
        print(f"[Encode]   {p.encoding_percentage:.1f}%  fps={p.encoding_fps}  speed={p.encoding_speed}")
    elif p.status == ProgressStatus.MERGING:
        print("[Merging streams...]")
    elif p.status == ProgressStatus.COMPLETED:
        print("Done!")

downloader = AsyncYT()
await downloader.setup_binaries()
await downloader.download("https://youtu.be/dQw4w9WgXcQ", progress_callback=on_progress)
```

### DownloadProgress fields

| Field                 | Description                                                                     |
| --------------------- | ------------------------------------------------------------------------------- |
| `id`                  | Download ID (SHA-256 hash of URL + config)                                      |
| `url`                 | Download URL                                                                    |
| `title`               | Video title                                                                     |
| `status`              | Current phase (`downloading`, `encoding`, `merging`, `remuxing`, `completed` …) |
| `percentage`          | Download progress 0–100                                                         |
| `downloaded_bytes`    | Bytes downloaded so far                                                         |
| `total_bytes`         | Total bytes expected                                                            |
| `speed`               | Download speed string, e.g. `"3.20MiB/s"`                                       |
| `eta`                 | Estimated seconds remaining                                                     |
| `encoding_percentage` | FFmpeg encode progress 0–100                                                    |
| `encoding_fps`        | Frames per second during encoding                                               |
| `encoding_speed`      | Encoding speed multiplier, e.g. `"2.50x"`                                       |
| `encoding_frame`      | Current frame being encoded                                                     |
| `encoding_bitrate`    | Current output bitrate during encode                                            |
| `encoding_size`       | Output size so far during encode                                                |
| `encoding_time`       | Elapsed encode time as `HH:MM:SS.mmm`                                           |

---

## 🔍 Search

```python
results = await downloader.search("Eminem - Mockingbird", max_results=5)
for video in results:
    print(video.title, video.url, video.duration)
```

---

## 📋 Playlist Download

```python
from asyncyt.basemodels import PlaylistRequest, DownloadConfig
from asyncyt.enums import Quality

request = PlaylistRequest(
    url="https://www.youtube.com/playlist?list=PL...",
    config=DownloadConfig(quality=Quality.HD_720P),
    max_videos=20,
)

response = await downloader.download_playlist(request=request)
print(f"Downloaded {response.successful_downloads} of {response.total_videos}")
print("Failed:", response.failed_downloads)
```

---

## ⚙️ DownloadConfig Reference

| Field              | Default         | Description                                      |
| ------------------ | --------------- | ------------------------------------------------ |
| `output_path`      | `"./downloads"` | Output directory (created automatically)         |
| `quality`          | `Quality.BEST`  | Video quality setting                            |
| `audio_format`     | `None`          | Audio format for extraction                      |
| `video_format`     | `None`          | Video container format                           |
| `extract_audio`    | `False`         | Extract audio only                               |
| `embed_subs`       | `False`         | Embed subtitles in video                         |
| `write_subs`       | `False`         | Write subtitle files                             |
| `subtitle_lang`    | `"en"`          | Subtitle language code                           |
| `write_thumbnail`  | `False`         | Download thumbnail                               |
| `embed_thumbnail`  | `False`         | Embed thumbnail in file                          |
| `embed_metadata`   | `True`          | Embed metadata                                   |
| `write_info_json`  | `False`         | Write yt-dlp info JSON                           |
| `write_live_chat`  | `False`         | Download live chat                               |
| `custom_filename`  | `None`          | Custom yt-dlp output template                    |
| `cookies_file`     | `None`          | Path to cookies file                             |
| `proxy`            | `None`          | Proxy URL                                        |
| `rate_limit`       | `None`          | Rate limit e.g. `"1M"` or `"500K"`               |
| `retries`          | `3`             | Number of retries (0–10)                         |
| `fragment_retries` | `3`             | Fragment retries (0–10)                          |
| `custom_options`   | `{}`            | Extra yt-dlp options as key→value dict           |
| `encoding`         | `None`          | `EncodingConfig` for fine-grained FFmpeg control |

---

## 🎬 Available Enums

| Enum             | Values (examples)                                                                        |
| ---------------- | ---------------------------------------------------------------------------------------- |
| `Quality`        | `BEST`, `WORST`, `AUDIO_ONLY`, `VIDEO_ONLY`, `HD_720P`, `HD_1080P`, `UHD_4K`, `UHD_8K` … |
| `VideoFormat`    | `MP4`, `MKV`, `WEBM`, `AVI`, `MOV`, `FLV`, `GIF`                                         |
| `AudioFormat`    | `MP3`, `AAC`, `FLAC`, `OPUS`, `OGG`, `WAV`, `ALAC` …                                     |
| `VideoCodec`     | `H264`, `H265`, `VP9`, `AV1`, `H264_NVENC`, `HEVC_NVENC`, `H264_QSV` …                   |
| `AudioCodec`     | `AAC`, `MP3`, `OPUS`, `FLAC`, `ALAC`, `AC3`, `COPY` …                                    |
| `Preset`         | `ULTRAFAST`, `FAST`, `MEDIUM`, `SLOW`, `VERYSLOW`, `PLACEBO` …                           |
| `TuneOption`     | `FILM`, `ANIMATION`, `GRAIN`, `FASTDECODE`, `ZEROLATENCY` …                              |
| `PixelFormat`    | `YUV420P`, `YUV420P10LE`, `YUV444P`, `RGB24`, `RGBA` …                                   |
| `AudioChannels`  | `MONO`, `STEREO`, `SURROUND_5_1`, `SURROUND_7_1`                                         |
| `ProgressStatus` | `DOWNLOADING`, `ENCODING`, `MERGING`, `REMUXING`, `COMPLETED` …                          |

---

## ⚠️ Exceptions

All exceptions extend `AsyncYTBase`.

| Exception                    | When raised                                        |
| ---------------------------- | -------------------------------------------------- |
| `DownloadAlreadyExistsError` | A download with the same ID is already running     |
| `DownloadNotFoundError`      | Attempting to cancel a download that doesn't exist |
| `DownloadGotCanceledError`   | A download was cancelled                           |
| `YtdlpDownloadError`         | yt-dlp exited with a non-zero return code          |
| `YtdlpSearchError`           | yt-dlp search failed                               |
| `YtdlpGetInfoError`          | yt-dlp failed to retrieve video info               |
| `YtdlpPlaylistGetInfoError`  | yt-dlp failed to retrieve playlist info            |

```python
from asyncyt.exceptions import AsyncYTBase, YtdlpDownloadError

try:
    await downloader.download(url, config)
except YtdlpDownloadError as e:
    print(f"yt-dlp failed (code {e.error_code}):\n{e.output}")
except AsyncYTBase as e:
    print(f"AsyncYT error: {e}")
```

---

## 🌐 Supported Sites

AsyncYT supports **1000+ websites** through yt-dlp, including:

- YouTube, YouTube Music
- Twitch, TikTok, Instagram
- Twitter, Reddit, Facebook
- Vimeo, Dailymotion, and many more

[See full list of supported sites →](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

---

## 📖 Documentation

👉 [Read the Docs](https://asyncyt.mahirou.online/)

---

## 🤝 Contributing

Contributions are welcome! Feel free to open an issue or pull request.

---

## 📜 License

MIT © **MahiroX36**
