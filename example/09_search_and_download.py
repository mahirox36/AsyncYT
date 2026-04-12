"""
09_search_and_download.py
-----------------------------------
Search for a query, display results, and download the chosen video.
"""

import asyncio
from asyncyt import AsyncYT
from asyncyt.basemodels import DownloadConfig, DownloadProgress, SearchRequest
from asyncyt.enums import AudioFormat, Quality


def format_duration(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


async def on_progress(p: DownloadProgress):
    if p.status == "downloading":
        print(f"\r⬇  {p.percentage:.1f}%  {p.speed}", end="", flush=True)
    elif p.status == "encoding":
        print(f"\r🎵 {p.encoding_percentage:.1f}%", end="", flush=True)
    elif p.status == "completed":
        print("\n✅ Done!")


async def main():
    yt = AsyncYT()
    await yt.setup_binaries()

    query = "Eminem - Mockingbird"
    print(f'Searching for: "{query}"\n')

    response = await yt.search(request=SearchRequest(query=query, max_results=5))

    if not response.success:
        print(f"Search failed: {response.error}")
        return

    # Display results
    for i, video in enumerate(response.results):
        print(f"  {i + 1}. {video.title}")
        print(f"     {video.uploader} · {format_duration(video.duration)} · {video.view_count:,} views")
        print()

    # Pick the first result automatically (in a real app, ask the user)
    chosen = response.results[0]
    print(f'Downloading: "{chosen.title}"\n')

    config = DownloadConfig(
        output_path="./downloads/search",
        quality=Quality.AUDIO_ONLY,
        extract_audio=True,
        audio_format=AudioFormat.MP3,
        embed_thumbnail=True,
        embed_metadata=True,
    )

    path = await yt.download(chosen.url, config, on_progress)
    print(f"Saved: {path}")


asyncio.run(main())
