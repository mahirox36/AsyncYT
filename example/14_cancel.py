"""
12_cancel.py
----------------------
Shows how to cancel a running download.
The download ID is returned from get_id() (same hash used internally),
or you can call cancel() from a separate task.
"""

import asyncio
from asyncyt import AsyncYT
from asyncyt.basemodels import DownloadConfig, DownloadProgress
from asyncyt.enums import Quality, VideoFormat
from asyncyt.utils import get_id


async def main():
    yt = AsyncYT()
    await yt.setup_binaries()

    config = DownloadConfig(
        output_path="./downloads/cancel_test",
        quality=Quality.HD_1080P,
        video_format=VideoFormat.MP4,
    )

    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    download_id = get_id(url, config)

    async def on_progress(p: DownloadProgress):
        print(f"  ⬇  {p.percentage:.1f}%")

    async def cancel_after(seconds: float):
        await asyncio.sleep(seconds)
        print(f"\n⛔ Cancelling download '{download_id}' …")
        try:
            await yt.cancel(download_id)
            print("  Download cancelled successfully.")
        except Exception as e:
            print(f"  Cancel error: {e}")

    # Start download and cancel tasks concurrently
    download_task = asyncio.create_task(
        yt.download(url, config, on_progress)
    )
    cancel_task = asyncio.create_task(cancel_after(10))   # cancel after 5 s

    try:
        await asyncio.gather(download_task, cancel_task)
    except Exception as e:
        print(f"\nCaught: {type(e).__name__}: {e}")


asyncio.run(main())
