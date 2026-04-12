"""
13_playlist_cancel.py
---------------------
Shows how to cancel a running playlist download after a timeout.

cancel_playlist(playlist_id) signals the playlist loop to stop after the
currently downloading video finishes — no video is left half-downloaded.

The playlist_id is just get_id(url, item_config), which you can compute
before starting the download, so you can store it and cancel from anywhere
(e.g. a keyboard shortcut, a web endpoint, a timeout).
"""

import asyncio
from asyncyt import AsyncYT
from asyncyt.basemodels import DownloadConfig, PlaylistConfig, PlaylistDownloadProgress
from asyncyt.enums import Quality
from asyncyt.exceptions import PlaylistCancelledError
from asyncyt.utils import get_id


async def on_progress(pl: PlaylistDownloadProgress) -> None:
    vp = pl.current_video_progress
    cv = pl.current_video

    if pl.status == "fetching_info":
        print(f"\r🔍  Fetching …", end="", flush=True)
        return

    if cv and vp is None:
        print(f"\n▶  [{pl.current_index}/{pl.total_videos}] {cv.title[:60] if cv.title else '…'}")
        return

    if vp:
        if vp.status == "downloading":
            print(f"\r   ⬇  {vp.percentage:.1f}%  {vp.speed}", end="", flush=True)
        elif vp.status == "encoding":
            print(f"\r   🔧  encode {vp.encoding_percentage:.1f}%", end="", flush=True)
        elif vp.status == "completed":
            print(f"\r   ✅  done                    ")


async def main():
    yt = AsyncYT()
    await yt.setup_binaries()

    PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLbpi6ZahtOH6Ar_3GPy3workEnjoment"

    item_config = DownloadConfig(
        output_path="./downloads/cancelled_test",
        quality=Quality.HD_720P,
        embed_metadata=True,
    )

    playlist_cfg = PlaylistConfig(
        item_config=item_config,
        max_videos=20,      # try to grab 20 — we'll cancel before that
        concurrency=1,
        skip_on_error=True,
    )

    # Compute the playlist_id before starting so we can pass it to cancel_playlist
    playlist_id = get_id(PLAYLIST_URL, item_config)
    print(f"Playlist ID: {playlist_id[:16]}…\n")

    async def _cancel_after(seconds: float) -> None:
        """Wait, then request cancellation."""
        await asyncio.sleep(seconds)
        print(f"\n\n⛔  Requesting cancel after {seconds}s …")
        try:
            await yt.cancel_playlist(playlist_id)
        except Exception as e:
            print(f"   (cancel error: {e})")

    # Run the download and the cancel-trigger concurrently
    download_task = asyncio.create_task(
        yt.download_playlist(
            url=PLAYLIST_URL,
            playlist_config=playlist_cfg,
            progress_callback=on_progress,
        )
    )
    cancel_task = asyncio.create_task(_cancel_after(30))   # cancel after 30 s

    try:
        response = await download_task
        cancel_task.cancel()    # download finished before cancel fired

    except PlaylistCancelledError as exc:
        cancel_task.cancel()
        print(f"\nPlaylist cancelled — got {exc.completed}/{exc.total} videos.")
        return

    # ── Summary (if not cancelled) ────────────────────────────────────────────
    print(f"\n\n{'='*50}")
    pl_title = response.playlist_info.title if response.playlist_info else "N/A"
    print(f"  Playlist : {pl_title}")
    print(f"  Done     : {response.successful_downloads}/{response.total_videos}")
    print(f"  Failed   : {response.failed_downloads}")
    print(f"{'='*50}")

    for item in response.results:
        icon = "✅" if item.success else "❌"
        print(f"  {icon}  [{item.index}] {item.video_info.title[:50] if item.video_info.title else '…'}")


asyncio.run(main())
