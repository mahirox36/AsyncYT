"""
12_playlist_download.py
-----------------------
Download a playlist with real-time per-video progress AND an overall
playlist progress bar.

Features shown
--------------
* PlaylistConfig  — concurrency, index ranges, skip-on-error
* PlaylistDownloadProgress  — overall %, current video info + its thumbnail
* Per-video DownloadProgress  — download % and live FFmpeg encoding fields
* PlaylistResponse  — per-item results with success/failure detail
"""

import asyncio
from asyncyt import AsyncYT
from asyncyt.basemodels import (
    DownloadConfig,
    PlaylistConfig,
    PlaylistRequest,
    PlaylistDownloadProgress,
)
from asyncyt.encoding import EncodingConfig, AudioEncodingConfig
from asyncyt.enums import AudioCodec, AudioFormat, Quality


# ── pretty helpers ────────────────────────────────────────────────────────────

def _bar(pct: float, width: int = 20) -> str:
    filled = int(width * pct / 100)
    return "█" * filled + "░" * (width - filled)


async def on_playlist_progress(pl: PlaylistDownloadProgress) -> None:
    """Called on every meaningful change — overall state or per-video progress."""

    status = pl.status
    overall = pl.overall_percentage
    done = pl.completed_videos
    total = pl.total_videos

    # ── Overall header (always printed) ─────────────────────────────────────
    overall_line = (
        f"Playlist [{_bar(overall)}] {overall:.1f}%  "
        f"({done}/{total} done, {pl.failed_videos} failed)"
    )

    if status == "fetching_info":
        print(f"\r🔍  Fetching playlist info …", end="", flush=True)
        return

    vp = pl.current_video_progress
    cv = pl.current_video

    if cv is None:
        print(f"\r{overall_line}", end="", flush=True)
        return

    video_title = (cv.title or "…")[:55]

    if vp is None:
        # About to start this video
        print(f"\n▶  [{pl.current_index}/{total}] {video_title}")
        if cv.thumbnail:
            print(f"   🖼  {cv.thumbnail}")
        return

    # ── Per-video progress line ──────────────────────────────────────────────
    vstatus = vp.status

    if vstatus == "downloading":
        speed = f"  {vp.speed}" if vp.speed else ""
        eta   = f"  ETA {vp.eta}s" if vp.eta else ""
        video_line = f"   ⬇  {_bar(vp.percentage)} {vp.percentage:.1f}%{speed}{eta}"

    elif vstatus == "encoding":
        enc_pct = vp.encoding_percentage
        extras = []
        if vp.encoding_fps:
            extras.append(f"{vp.encoding_fps:.0f} fps")
        if vp.encoding_speed:
            extras.append(vp.encoding_speed)
        if vp.encoding_bitrate:
            extras.append(vp.encoding_bitrate)
        extra_str = "  " + "  ".join(extras) if extras else ""
        video_line = f"   🔧 encode {_bar(enc_pct)} {enc_pct:.1f}%{extra_str}"

    elif vstatus in ("merging", "remuxing"):
        video_line = f"   🔀 {vstatus} …"

    elif vstatus == "completed":
        video_line = f"   ✅ done"

    else:
        video_line = f"   … {vstatus}"

    # Overwrite current line
    print(f"\r{video_line:<70}", end="", flush=True)


# ── main ──────────────────────────────────────────────────────────────────────

async def main():
    yt = AsyncYT()
    await yt.setup_binaries()

    # Per-video encoding: download as 720p MP4, encode audio to AAC 192k
    item_config = DownloadConfig(
        output_path="./downloads/playlist",
        quality=Quality.HD_720P,
        video_format=None,          # keep whatever container yt-dlp picks
        embed_metadata=True,
        embed_thumbnail=True, # mostly will fails cuz mostly it will save it as mkv and that doesn't support embedded thumbnails, but we'll try anyway
        encoding=EncodingConfig(
            audio=AudioEncodingConfig(
                codec=AudioCodec.AAC,
                bitrate="192k",
                sample_rate=44100,
            )
        ),
    )

    playlist_cfg = PlaylistConfig(
        item_config=item_config,
        max_videos=5,           # grab the first 5 only
        start_index=1,          # 1-based; change to e.g. 3 to skip the first two
        concurrency=1,          # sequential — friendlier for YouTube rate limits
        skip_on_error=True,     # log failed videos and keep going
    )

    request = PlaylistRequest(
        url="https://www.youtube.com/playlist?list=PLo_mCdoeO0g9WdS38ko_bpVWPp23DvxPr",
        playlist_config=playlist_cfg,
    )

    print("Starting playlist download …\n")

    response = await yt.download_playlist(
        request=request,
        progress_callback=on_playlist_progress,
    )

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n\n{'='*55}")
    print(f"  Playlist : {response.playlist_info.title if response.playlist_info else 'N/A'}")
    print(f"  Done     : {response.successful_downloads}/{response.total_videos}")
    print(f"  Failed   : {response.failed_downloads}")
    print(f"{'='*55}")

    for item in response.results:
        icon = "✅" if item.success else "❌"
        name = item.video_info.title or item.video_info.url
        detail = item.filepath if item.success else item.error
        print(f"  {icon}  [{item.index}] {name[:50]}")
        print(f"          {detail}")


asyncio.run(main())
