# Usage

AsyncYT is fully async and easy to use. Here are the basics:

## Basic Download

```py
from asyncyt import Downloader
import asyncio

downloader = Downloader()

async def main():
    await downloader.setup_binaries()
    await downloader.download('https://www.youtube.com/watch?v=dQw4w9WgXcQ')

asyncio.run(main())
```

## Get Video Info

```py
info = await downloader.get_video_info('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
print(info.title, info.duration)
```

## Download with Progress

```py
def on_progress(progress):
    print(f"{progress.title}: {progress.percentage:.2f}%")

await downloader.download(
    'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    progress_callback=on_progress
)
```

## Search YouTube

```py
results = await downloader.search('python tutorial', max_results=5)
for video in results:
    print(video.title, video.url)
```

---

See [API Reference](./api.md) for all available methods.
