# Configuration

AsyncYT uses `DownloadConfig` to control download behavior.

## DownloadConfig Options

| Option            | Type                | Default         | Description                                 |
|-------------------|---------------------|-----------------|---------------------------------------------|
| output_path       | str                 | './downloads'   | Output directory for downloads              |
| quality           | Quality Enum        | 'best'          | Video quality (e.g. '720p', 'best')         |
| audio_format      | AudioFormat Enum    | None            | Audio format (e.g. 'mp3', 'm4a')            |
| video_format      | VideoFormat Enum    | None            | Video format (e.g. 'mp4', 'webm')           |
| extract_audio     | bool                | False           | Download audio only                         |
| embed_subs        | bool                | False           | Embed subtitles in video                    |
| write_subs        | bool                | False           | Write subtitle files                        |
| subtitle_lang     | str                 | 'en'            | Subtitle language code                      |
| write_thumbnail   | bool                | False           | Download thumbnail                          |
| embed_thumbnail   | bool                | False           | Embed thumbnail in file                     |
| write_info_json   | bool                | False           | Write info JSON file                        |
| custom_filename   | str or None         | None            | Custom filename template                    |
| cookies_file      | str or None         | None            | Path to cookies file                        |
| proxy             | str or None         | None            | Proxy URL                                   |
| rate_limit        | str or None         | None            | Download rate limit (e.g. '1M')             |
| retries           | int                 | 3               | Number of retries                           |
| fragment_retries  | int                 | 3               | Fragment retries                            |
| custom_options    | dict                | {{}}            | Custom yt-dlp options                       |

## Example

```py
from asyncyt import DownloadConfig

config = DownloadConfig(
    output_path='./myvids',
    quality='720p',
    extract_audio=True,
    audio_format='mp3',
    write_thumbnail=True,
    embed_thumbnail=True,
    subtitle_lang='en',
    retries=5,
)
```

---

See [API Reference](./api.md) for more details.
