# Examples

## Download a Video

```py
from asyncyt import Downloader
import asyncio

downloader = Downloader()

async def main():
    await downloader.setup_binaries()
    await downloader.download('https://www.youtube.com/watch?v=dQw4w9WgXcQ')

asyncio.run(main())
```

## Download with Custom Config

```py
from asyncyt import Downloader, DownloadConfig
import asyncio

downloader = Downloader()
config = DownloadConfig(quality='720p', extract_audio=True, audio_format='mp3')

async def main():
    await downloader.setup_binaries()
    await downloader.download('https://www.youtube.com/watch?v=dQw4w9WgXcQ', config)

asyncio.run(main())
```

## Download Playlist

```py
from asyncyt import Downloader
import asyncio

downloader = Downloader()

async def main():
    await downloader.setup_binaries()
    files = await downloader.download_playlist('https://www.youtube.com/playlist?list=PL12345')
    print(files)

asyncio.run(main())
```

## Search and Download First Result

```py
from asyncyt import Downloader
import asyncio

downloader = Downloader()

async def main():
    await downloader.setup_binaries()
    results = await downloader.search('python tutorial')
    if results:
        await downloader.download(results[0].url)

asyncio.run(main())
```

---

See [Usage](./usage.md) for more details.
