"""
11_playlist_info.py
-------------------
Fetch full playlist metadata — titles, durations, thumbnails — without
downloading a single byte of video.

Useful for building a "pick what you want" UI or just previewing a playlist
before committing to a download.
"""

import asyncio
from asyncyt import AsyncYT


async def main():
    yt = AsyncYT()
    await yt.setup_binaries()

    PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLo_mCdoeO0g9WdS38ko_bpVWPp23DvxPr"

    print("Fetching playlist info …\n")
    info = await yt.get_playlist(PLAYLIST_URL)

    print(f"📋  {info.title}")
    print(f"👤  {info.uploader}")
    print(f"🎬  {info.entry_count} videos total")
    if info.thumbnail:
        print(f"🖼   Playlist thumbnail: {info.thumbnail}")
    print()

    for video in info:
        mins, secs = divmod(int(video.duration), 60)
        duration_str = f"{mins}:{secs:02d}" if video.duration else "?:??"

        print(f"  [{video.playlist_index:>3}]  {video.title}")
        print(f"         ⏱  {duration_str}   👁  {video.view_count:,}   📅  {video.upload_date}")
        print(f"         🖼  {video.thumbnail}")
        print()

    # You can also access individual entries by index
    first = info[0]
    print(f"First video URL  : {first.url}")
    print(f"Total entries    : {len(info)}")


asyncio.run(main())