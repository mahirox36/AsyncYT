# AsyncYT Documentation

Welcome to **AsyncYT** 🧠✨
A YouTube downloader that’s cute, clean, and async from top to bottom!

## Table of Contents

- [Installation](./installation.md)
- [Quickstart](#quickstart)
- [Usage](./usage.md)
- [API Reference](./api.md)
- [Configuration](./config.md)
- [Examples](./examples.md)

---

## Quickstart

```py
from asyncyt import Downloader
import asyncio

downloader = Downloader()

async def main():
    await downloader.setup_binaries()
    info = await downloader.get_video_info('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
    print(info.title)
    await downloader.download('https://www.youtube.com/watch?v=dQw4w9WgXcQ')

asyncio.run(main())
```

---

See [Installation](./installation.md) to get started, or [Usage](./usage.md) for more details.
