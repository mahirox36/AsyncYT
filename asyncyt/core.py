"""
core.py
-------
AsyncYT core downloader.  Contains the main :class:`AsyncYT` class with methods for video info retrieval, single-video download, playlist download, and search.  Also includes internal helper functions and the
``_FfmpegProgressParser`` class for parsing FFmpeg progress output.  Exceptions are defined in :mod:`exceptions.py` and data models in :mod:`basemodels.py`.  Binary management is handled by :mod:`binaries.py`.
"""

from __future__ import annotations

import asyncio
import logging
import os
import platform
import re
import shutil
import signal
import tempfile
import warnings
from json import loads
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union, overload
from collections.abc import Callable as CallableABC

from .basemodels import (
    DownloadConfig,
    DownloadProgress,
    DownloadRequest,
    DownloadResponse,
    PlaylistConfig,
    PlaylistDownloadProgress,
    PlaylistInfo,
    PlaylistItemResult,
    PlaylistRequest,
    PlaylistResponse,
    PlaylistVideoInfo,
    SearchRequest,
    SearchResponse,
    VideoInfo,
)
from .builder import build_download_command
from .enums import PlaylistStatus, ProgressStatus
from .exceptions import (
    AsyncYTBase,
    DownloadAlreadyExistsError,
    DownloadGotCanceledError,
    DownloadNotFoundError,
    PlaylistCancelledError,
    PlaylistDownloadError,
    YtdlpDownloadError,
    YtdlpGetInfoError,
    YtdlpPlaylistGetInfoError,
    YtdlpSearchError,
)
from .utils import (
    call_callback,
    clean_youtube_url,
    get_id,
    get_unique_filename,
    get_unique_path,
)
from .binaries import BinaryManager

logger = logging.getLogger(__name__)

__all__ = ["AsyncYT"]

_IS_WINDOWS = platform.system().lower() == "windows"


# [download]  45.3% of ~  50.00MiB at    3.20MiB/s ETA 00:08
_RE_DOWNLOAD = re.compile(
    r"\[download\]\s+"
    r"(?P<pct>[\d.]+)%"
    r"(?:\s+of\s+~?\s*(?P<total>[\d.]+\s*\S+))?"
    r"(?:\s+at\s+(?P<speed>[\d.]+\s*\S+/s))?"
    r"(?:\s+ETA\s+(?P<eta>[\d:]+))?"
)

_RE_MERGER = re.compile(r"\[Merger\]", re.IGNORECASE)
_RE_CONVERTOR = re.compile(r"\[VideoConvertor\]|\[ExtractAudio\]", re.IGNORECASE)
_RE_REMUXER = re.compile(r"\[VideoRemuxer\]", re.IGNORECASE)
_RE_DESTINATION = re.compile(
    r"(?:\[download\] Destination:|Merging formats into)\s+(.+)"
)

# FFmpeg -progress key=value line (e.g. "out_time=00:00:05.123456")
_RE_FFMPEG_KV = re.compile(r"^(?P<key>[a-zA-Z_]+)=(?P<value>.+)$")


def _parse_eta(eta_str: str) -> int:
    parts = eta_str.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(float(parts[2]))
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(float(parts[1]))
        return int(float(parts[0]))
    except (ValueError, IndexError):
        return 0


def _out_time_to_seconds(t: str) -> float:
    """Convert 'HH:MM:SS.ffffff' or 'SS.ffffff' to float seconds."""
    try:
        t = t.strip()
        parts = t.split(":")
        if len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        if len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        return float(parts[0])
    except (ValueError, IndexError):
        return 0.0


def _bytes_to_human(n: int) -> str:
    for unit in ("B", "KiB", "MiB", "GiB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n //= 1024
    return f"{n:.1f}TiB"


class _FfmpegProgressParser:
    """
    Stateful parser for FFmpeg ``-progress pipe:1`` key=value blocks.

    FFmpeg emits groups of key=value pairs terminated by
    ``progress=continue`` or ``progress=end``.  We accumulate the block
    and flush it once we see the terminator.
    """

    def __init__(self, progress: DownloadProgress, total_duration: float):
        self.progress = progress
        self.total_duration = total_duration
        self._block: Dict[str, str] = {}

    def feed(self, line: str) -> bool:
        """
        Feed one line.  Returns True if ``progress`` was updated.
        ``line`` should already be stripped.
        """
        m = _RE_FFMPEG_KV.match(line)
        if not m:
            return False

        key = m.group("key")
        value = m.group("value").strip()

        if key == "progress":
            changed = self._flush()
            self._block = {}
            if value == "end":
                self.progress.encoding_percentage = 100.0
                self.progress.status = ProgressStatus.ENCODING
                return True
            return changed

        self._block[key] = value
        return False

    def _flush(self) -> bool:
        b = self._block
        if not b:
            return False
        logger.debug(b)

        p = self.progress
        p.status = ProgressStatus.ENCODING
        changed = False

        if "frame" in b:
            try:
                new = int(b["frame"])
                if new != p.encoding_frame:  # ← only if changed
                    p.encoding_frame = new
                    changed = True
            except ValueError:
                pass

        if "fps" in b:
            try:
                val = float(b["fps"])
                if val > 0 and val != p.encoding_fps:  # ← only if changed
                    p.encoding_fps = val
                    changed = True
            except ValueError:
                pass

        if "bitrate" in b:
            new = b["bitrate"]
            if new != p.encoding_bitrate:  # ← only if changed
                p.encoding_bitrate = new
                changed = True

        if "total_size" in b:
            try:
                size_bytes = int(b["total_size"])
                if size_bytes > 0:
                    human = _bytes_to_human(size_bytes)
                    if human != p.encoding_size:  # ← only if changed
                        p.encoding_size = human
                        changed = True
            except ValueError:
                pass

        if "speed" in b:
            raw = b["speed"].strip()
            if raw and raw != "N/A" and raw != p.encoding_speed:  # ← only if changed
                p.encoding_speed = raw
                changed = True

        if "out_time" in b:
            raw_time = b["out_time"].strip()
            if not raw_time.startswith("-"):
                if raw_time != p.encoding_time:
                    p.encoding_time = raw_time
                    changed = True  # ← always fire when time moves
                elapsed = _out_time_to_seconds(raw_time)
                if self.total_duration > 0:
                    pct = min(round((elapsed / self.total_duration) * 100, 2), 100.0)
                    if pct != p.encoding_percentage:
                        p.encoding_percentage = pct
                        changed = True

        return changed


def _update_download_progress(
    line: str,
    progress: DownloadProgress,
    ffmpeg_parser: _FfmpegProgressParser,
) -> bool:
    """
    Parse one line of yt-dlp (or embedded FFmpeg) output.
    Returns True if ``progress`` changed and the callback should fire.
    """
    stripped = line.strip()

    # --- FFmpeg -progress pipe:1 key=value lines ---
    # These are interleaved with yt-dlp output when using --external-downloader ffmpeg
    if _RE_FFMPEG_KV.match(stripped):
        return ffmpeg_parser.feed(stripped)

    # --- Phase change markers ---
    if _RE_MERGER.search(line):
        if progress.status != ProgressStatus.MERGING:
            progress.status = ProgressStatus.MERGING
            return True
        return False

    if _RE_CONVERTOR.search(line):
        if progress.status != ProgressStatus.ENCODING:
            progress.status = ProgressStatus.ENCODING
            progress.encoding_percentage = 0.0
            return True
        return False

    if _RE_REMUXER.search(line):
        if progress.status != ProgressStatus.REMUXING:
            progress.status = ProgressStatus.REMUXING
            return True
        return False

    # --- Title from destination line ---
    dm = _RE_DESTINATION.search(line)
    if dm:
        progress.title = Path(dm.group(1).strip()).stem
        return False

    # --- yt-dlp download progress line ---
    m = _RE_DOWNLOAD.search(line)
    if m:
        old_pct = progress.percentage
        progress.percentage = min(float(m.group("pct")), 100.0)
        if m.group("speed"):
            progress.speed = m.group("speed").strip()
        if m.group("eta"):
            progress.eta = _parse_eta(m.group("eta"))
        progress.status = ProgressStatus.DOWNLOADING
        return progress.percentage != old_pct

    return False


async def _kill_process(process: asyncio.subprocess.Process) -> None:
    """
    Terminate a process and all its children.

    On POSIX, we kill the entire process group.
    On Windows, we use ``taskkill /F /T`` to recursively kill the tree.
    """
    pid = process.pid
    try:
        if _IS_WINDOWS:
            kill_cmd = ["taskkill", "/F", "/T", "/PID", str(pid)]
            kill_proc = await asyncio.create_subprocess_exec(
                *kill_cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await kill_proc.wait()
        else:
            if hasattr(os, "killpg"):
                try:
                    pgid = os.getpgid(pid)  # type: ignore
                    os.killpg(pgid, signal.SIGKILL)  # type: ignore
                except ProcessLookupError:
                    pass
    except Exception as e:
        logger.warning("Failed to kill process %s: %s", pid, e)
    finally:
        try:
            await process.wait()
        except Exception:
            pass


async def _read_process_output(process: asyncio.subprocess.Process):
    """Async generator yielding decoded stdout lines."""
    assert process.stdout is not None
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        yield line.decode("utf-8", errors="replace")


class AsyncYT(BinaryManager):
    """
    AsyncYT: Asynchronous media downloader powered by yt-dlp.

    Supports single-video downloads, audio extraction, YouTube search,
    and native playlist downloads — all with real-time progress callbacks.

    FFmpeg encoding/download progress is captured via
    ``--external-downloader ffmpeg -progress pipe:1`` so you receive
    accurate frame, fps, speed, bitrate, size, and percentage updates.

    :param bin_dir: Directory containing yt-dlp (and optionally ffmpeg) binaries.
    """

    def __init__(self, bin_dir=None):
        super().__init__(bin_dir=bin_dir)
        # Maps download_id → asyncio subprocess (single videos)
        self._downloads: Dict[str, asyncio.subprocess.Process] = {}
        # Maps playlist_id → asyncio.Event (set to request cancellation)
        self._playlist_cancel_events: Dict[str, asyncio.Event] = {}

    async def get_video_info(self, url: str) -> VideoInfo:
        """
        Retrieve video metadata from *url* using yt-dlp.

        :param url: Video URL.
        :return: :class:`VideoInfo` with title, duration, thumbnail, etc.
        :raises YtdlpGetInfoError: If yt-dlp returns a non-zero exit code.
        """
        url = clean_youtube_url(url)
        cmd = [str(self.ytdlp_path), "--dump-json", "--no-warnings", url]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise YtdlpGetInfoError(url, process.returncode, stderr.decode())
        return VideoInfo.from_dict(loads(stdout.decode()))

    async def get_playlist_info(
        self,
        url: str,
        max_videos: Optional[int] = None,
    ) -> PlaylistInfo:
        """
        Fetch full playlist metadata, including per-video thumbnails.

        Uses yt-dlp's ``--flat-playlist`` so it is fast — no individual
        video pages are fetched.  Thumbnails come from the flat data that
        YouTube/yt-dlp provides in the playlist manifest.

        :param url: Playlist URL.
        :param max_videos: Limit to this many entries (None = all).
        :return: :class:`PlaylistInfo` with all :class:`PlaylistVideoInfo` entries.
        :raises YtdlpPlaylistGetInfoError: If yt-dlp fails.
        """
        cmd = [
            str(self.ytdlp_path),
            "--dump-json",
            "--flat-playlist",
            "--no-warnings",
            url,
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise YtdlpPlaylistGetInfoError(url, process.returncode, stderr.decode())

        raw_lines = stdout.decode().strip().splitlines()
        raw_entries = [loads(line) for line in raw_lines if line.strip()]

        return PlaylistInfo.from_ytdlp(
            raw_entries, playlist_url=url, max_videos=max_videos
        )

    async def _search(self, query: str, max_results: int = 10) -> List[VideoInfo]:
        """Internal YouTube search via yt-dlp."""
        search_url = f"ytsearch{max_results}:{query}"
        cmd = [
            str(self.ytdlp_path),
            "--dump-json",
            "--no-warnings",
            "--match-filter",
            "live_status = 'not_live' & duration > 0",
            search_url,
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise YtdlpSearchError(query, process.returncode, stderr.decode())
        return [
            VideoInfo.from_dict(loads(line))
            for line in stdout.decode().strip().splitlines()
            if line.strip()
        ]

    def _get_config(self, *args, **kwargs):
        """
        Parse positional / keyword arguments into ``(url, config, callback, finalize)``.

        Accepts:
        - ``(url: str, config: DownloadConfig, callback, finalize: bool)`` positionally
        - ``url=``, ``config=``, ``progress_callback=``, ``finalize=`` as kwargs
        - A :class:`DownloadRequest` as first positional arg or ``request=`` kwarg
        """
        url: Optional[str] = None
        config: Optional[DownloadConfig] = None
        progress_callback = None
        finalize: bool = True

        if "url" in kwargs:
            url = kwargs["url"]
        if "config" in kwargs:
            config = kwargs["config"]
        if "progress_callback" in kwargs:
            progress_callback = kwargs["progress_callback"]
        if "finalize" in kwargs:
            finalize = kwargs["finalize"]
        if "request" in kwargs:
            req = kwargs["request"]
            url = req.url
            config = req.config

        for arg in args:
            if isinstance(arg, str):
                url = arg
            elif isinstance(arg, DownloadConfig):
                config = arg
            elif isinstance(arg, bool):
                finalize = arg
            elif isinstance(arg, CallableABC):
                progress_callback = arg
            elif isinstance(arg, DownloadRequest):
                url = arg.url
                config = arg.config

        if not url:
            raise TypeError("url is required")
        return url, config, progress_callback, finalize

    async def finalize_download(
        self,
        temp_dir: Union[tempfile.TemporaryDirectory, Path],
        output_dir: Path,
        config: DownloadConfig,
    ) -> List[Path]:
        """
        Move processed files from *temp_dir* to *output_dir*.

        :param temp_dir: Temporary directory (cleaned up afterwards).
        :param output_dir: Final destination directory.
        :param config: Download config (used for overwrite setting).
        :return: List of moved :class:`Path` objects.
        """
        moved: List[Path] = []
        td = (
            Path(temp_dir.name)
            if isinstance(temp_dir, tempfile.TemporaryDirectory)
            else temp_dir
        )
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            for item in td.iterdir():
                if item.is_dir():
                    continue
                dest = output_dir / item.name
                overwrite = config.encoding.overwrite if config.encoding else False
                if dest.exists():
                    destination = (
                        dest
                        if overwrite
                        else Path(get_unique_path(output_dir, item.name))
                    )
                else:
                    destination = dest
                try:
                    await asyncio.to_thread(shutil.move, str(item), str(destination))
                    logger.debug("Moved %s → %s", item, destination)
                    moved.append(destination)
                except Exception as e:
                    logger.error("Failed to move %s → %s: %s", item, destination, e)
                    raise
        finally:
            try:
                if isinstance(temp_dir, Path):
                    if temp_dir.exists():
                        await asyncio.to_thread(shutil.rmtree, temp_dir)
                else:
                    await asyncio.to_thread(temp_dir.cleanup)
            except Exception as e:
                logger.warning("Failed to clean temp dir: %s", e)
        return moved

    @overload
    async def download(
        self,
        url: str,
        config: Optional[DownloadConfig] = None,
        progress_callback: Optional[
            Callable[[DownloadProgress], Union[None, Awaitable[None]]]
        ] = None,
        finalize: bool = True,
    ) -> Path: ...

    @overload
    async def download(
        self,
        request: DownloadRequest,
        progress_callback: Optional[
            Callable[[DownloadProgress], Union[None, Awaitable[None]]]
        ] = None,
        finalize: bool = True,
    ) -> Path: ...

    async def download(self, *args, **kwargs) -> Path:
        """
        Download a single video (or audio) from *url*.

        :param url: Video URL **or** a :class:`DownloadRequest`.
        :param config: Optional :class:`DownloadConfig`.
        :param progress_callback: Async or sync callable receiving :class:`DownloadProgress`.
        :param finalize: Move output from temp dir to ``config.output_path``.
        :return: :class:`Path` to the downloaded file.
        :raises DownloadAlreadyExistsError: Same download already running.
        :raises YtdlpDownloadError: yt-dlp returned a non-zero exit code.
        :raises DownloadGotCanceledError: :meth:`cancel` was called.
        :raises FileNotFoundError: FFmpeg not found, or no output file produced.
        """
        url, config, progress_callback, finalize = self._get_config(*args, **kwargs)
        config = config or DownloadConfig()
        url = clean_youtube_url(url)
        id_ = get_id(url, config)

        if id_ in self._downloads:
            raise DownloadAlreadyExistsError(id_)

        output_dir = Path(config.output_path).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        if not self.ffmpeg_path:
            raise FileNotFoundError("FFmpeg is not installed / not found")

        # Temp dir — yt-dlp writes here first; we move on completion
        temp_dir = tempfile.TemporaryDirectory(delete=False)
        temp_path = Path(temp_dir.name)
        config_for_run = config.model_copy(update={"output_path": str(temp_path)})

        # Pre-fetch duration for encoding_percentage calculation
        total_duration = 0.0
        try:
            info = await self.get_video_info(url)
            total_duration = float(info.duration or 0)
        except Exception as e:
            logger.warning(
                "Could not fetch video duration (percentage will be unavailable): %s", e
            )

        cmd = build_download_command(
            ytdlp_path=str(self.ytdlp_path),
            ffmpeg_path=str(self.ffmpeg_path),
            url=url,
            config=config_for_run,
        )
        logger.debug("yt-dlp command: %s", " ".join(cmd))

        progress = DownloadProgress(url=url, percentage=0.0, id=id_)
        ffmpeg_parser = _FfmpegProgressParser(progress, total_duration)
        last_pct = -1.0
        last_enc_pct = -1.0
        output: List[str] = []

        try:
            # On POSIX, start_new_session=True puts the child in its own
            # process group so we can killpg() the whole tree on cancel.
            kwargs_proc: Dict[str, Any] = dict(
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=temp_path,
            )
            if not _IS_WINDOWS:
                kwargs_proc["start_new_session"] = True

            process = await asyncio.create_subprocess_exec(*cmd, **kwargs_proc)
            self._downloads[id_] = process

            async for line in _read_process_output(process):
                output.append(line.rstrip())
                if not line.strip():
                    continue

                changed = _update_download_progress(
                    line.rstrip(), progress, ffmpeg_parser
                )

                if progress_callback and changed:
                    should_fire = False
                    if progress.status == ProgressStatus.ENCODING:
                        if progress.encoding_percentage != last_enc_pct:
                            last_enc_pct = progress.encoding_percentage
                            should_fire = True
                    else:
                        if progress.percentage != last_pct:
                            last_pct = progress.percentage
                            should_fire = True

                    if should_fire:
                        await call_callback(progress_callback, progress)

            returncode = await process.wait()

            if returncode != 0:
                raise YtdlpDownloadError(
                    url=url, output=output, cmd=cmd, error_code=returncode
                )

            # Completion
            progress.status = ProgressStatus.COMPLETED
            progress.percentage = 100.0
            progress.encoding_percentage = 100.0
            if progress_callback:
                await call_callback(progress_callback, progress)

            if finalize:
                moved = await self.finalize_download(temp_dir, output_dir, config)
                if moved:
                    logger.info("Download completed: %s", moved[0])
                    return moved[0]
                raise FileNotFoundError("No output file found after processing")

            files = [f for f in temp_path.iterdir() if f.is_file()]
            if files:
                return files[0]
            raise FileNotFoundError("No output file found in temp dir")

        except asyncio.CancelledError:
            proc = self._downloads.get(id_)
            if proc:
                await _kill_process(proc)
            raise DownloadGotCanceledError(id_)
        except Exception:
            raise
        finally:
            self._downloads.pop(id_, None)

    async def cancel(self, download_id: str) -> None:
        """
        Cancel a running single-video download.

        Kills the yt-dlp process **and** any child FFmpeg process.

        :param download_id: The ID returned by :func:`get_id`.
        :raises DownloadNotFoundError: If no download with that ID is running.
        """
        process = self._downloads.pop(download_id, None)
        if not process:
            raise DownloadNotFoundError(download_id)
        await _kill_process(process)

    async def cancel_playlist(self, playlist_id: str) -> None:
        """
        Request cancellation of a running playlist download.

        The playlist loop checks the cancel event between each video.
        The currently-downloading video is also cancelled immediately.

        :param playlist_id: The playlist ID returned by :func:`get_id`.
        :raises DownloadNotFoundError: If no playlist with that ID is running.
        """
        event = self._playlist_cancel_events.get(playlist_id)
        if not event:
            raise DownloadNotFoundError(playlist_id)
        event.set()

    async def download_with_response(self, *args, **kwargs) -> DownloadResponse:
        """
        Download with an API-friendly :class:`DownloadResponse` return value.

        Accepts the same arguments as :meth:`download`.

        :return: :class:`DownloadResponse` with metadata and optional error.
        """
        id_: Optional[str] = None
        try:
            url, config, progress_callback, finalize = self._get_config(*args, **kwargs)
            config = config or DownloadConfig()
            id_ = get_id(url, config)

            try:
                video_info = await self.get_video_info(url)
            except YtdlpGetInfoError as e:
                return DownloadResponse(
                    success=False,
                    message="Failed to get video information",
                    error=f"error code: {e.error_code}\nOutput: {e.output}",
                    id=id_,
                )
            except Exception as e:
                return DownloadResponse(
                    success=False,
                    message="Failed to get video information",
                    error=str(e),
                    id=id_,
                )

            filename = await self.download(url, config, progress_callback, finalize)
            file = Path(filename)
            new_file = get_unique_filename(
                file, re.sub(r'[\\/:"*?<>|]', "_", video_info.title)
            )
            file = file.rename(new_file)

            return DownloadResponse(
                success=True,
                message="Download completed successfully",
                filename=str(file.absolute()),
                video_info=video_info,
                id=id_,
            )
        except AsyncYTBase:
            raise
        except Exception as e:
            return DownloadResponse(
                success=False,
                message="Download failed",
                error=str(e),
                id=id_ or "",
            )

    async def search(
        self,
        query: Optional[str] = None,
        max_results: Optional[int] = None,
        *,
        request: Optional[SearchRequest] = None,
    ) -> SearchResponse:
        """
        Search YouTube for videos.

        :param query: Search query (required when *request* is not given).
        :param max_results: Maximum results (default 10, max 50).
        :param request: Optional :class:`SearchRequest` (mutually exclusive with *query*).
        :return: :class:`SearchResponse` with a list of :class:`VideoInfo` objects.
        """
        if request is not None:
            if query is not None or max_results is not None:
                raise TypeError("Provide request OR (query + max_results), not both.")
        else:
            if query is None:
                raise TypeError("query is required when request is not given.")
        if request:
            query = request.query
            max_results = request.max_results
        max_results = max_results or 10
        try:
            results = await self._search(query, max_results)  # type: ignore[arg-type]
            return SearchResponse(
                success=True,
                message=f"Found {len(results)} results",
                results=results,
                total_results=len(results),
            )
        except Exception as e:
            return SearchResponse(success=False, message="Search failed", error=str(e))

    async def get_playlist(
        self,
        url: str,
        max_videos: Optional[int] = None,
    ) -> PlaylistInfo:
        """
        Fetch playlist metadata without downloading any videos.

        :param url: Playlist URL.
        :param max_videos: Limit entries returned (None = all).
        :return: :class:`PlaylistInfo` with per-video :class:`PlaylistVideoInfo` entries
                 (each containing thumbnail URLs).
        """
        return await self.get_playlist_info(url, max_videos=max_videos)

    async def download_playlist(
        self,
        url: Optional[str] = None,
        playlist_config: Optional[PlaylistConfig] = None,
        progress_callback: Optional[
            Callable[[PlaylistDownloadProgress], Union[None, Awaitable[None]]]
        ] = None,
        *,
        request: Optional[PlaylistRequest] = None,
    ) -> PlaylistResponse:
        """
        Download all (or a subset of) videos from a playlist.

        Supports concurrent downloads via ``PlaylistConfig.concurrency``.
        Progress is reported through *progress_callback* with a
        :class:`PlaylistDownloadProgress` that includes both the overall
        playlist state and the current video's :class:`DownloadProgress`.

        :param url: Playlist URL (required when *request* is not given).
        :param playlist_config: Playlist-level configuration.
        :param progress_callback: Async or sync callable receiving
                                   :class:`PlaylistDownloadProgress` updates.
        :param request: Optional :class:`PlaylistRequest`.
        :return: :class:`PlaylistResponse` with per-item results and aggregated stats.
        :raises TypeError: If conflicting arguments are supplied.
        """
        if request is not None:
            if url is not None or playlist_config is not None:
                raise TypeError("Provide request OR (url + playlist_config), not both.")
        else:
            if url is None:
                raise TypeError("url is required when request is not given.")

        if request:
            url = request.url
            playlist_config = request.playlist_config

        playlist_config = playlist_config or PlaylistConfig()
        item_config = playlist_config.item_config or DownloadConfig()
        playlist_id = get_id(url, item_config)  # type: ignore[arg-type]

        # Create cancellation event
        cancel_event = asyncio.Event()
        self._playlist_cancel_events[playlist_id] = cancel_event

        # Live progress object
        pl_progress = PlaylistDownloadProgress(
            playlist_id=playlist_id,
            status=PlaylistStatus.FETCHING_INFO,
        )

        async def _emit() -> None:
            if progress_callback:
                await call_callback(progress_callback, pl_progress)

        await _emit()

        try:
            # --- Fetch playlist info ---
            try:
                # Always fetch the full playlist so video_indices and video_ids
                # can be resolved correctly against the complete entry list.
                # max_videos pre-limiting is applied later in the range-based path.
                playlist_info = await self.get_playlist_info(url, max_videos=None)  # type: ignore[arg-type]
            except YtdlpPlaylistGetInfoError as exc:
                raise PlaylistDownloadError(url, str(exc)) from exc  # type: ignore[arg-type]

            # Apply entry filtering — priority order:
            #   1. video_indices + video_ids  (explicit selection, union of both)
            #   2. start_index / end_index / max_videos  (range-based)
            entries = playlist_info.entries
            use_explicit = bool(
                playlist_config.video_indices or playlist_config.video_ids
            )

            if use_explicit:
                wanted_positions: set[int] = set()
                wanted_ids: set[str] = set()

                if playlist_config.video_indices:
                    wanted_positions = set(playlist_config.video_indices)

                if playlist_config.video_ids:
                    wanted_ids = set(playlist_config.video_ids)

                filtered: list[PlaylistVideoInfo] = []
                for entry in entries:
                    in_positions = (
                        entry.playlist_index is not None
                        and entry.playlist_index in wanted_positions
                    )
                    in_ids = bool(entry.id and entry.id in wanted_ids)
                    if in_positions or in_ids:
                        filtered.append(entry)

                # Warn about any requested indices / ids that matched nothing
                matched_positions = {
                    e.playlist_index for e in filtered if e.playlist_index is not None
                }
                matched_ids = {e.id for e in filtered if e.id}
                missing_pos = wanted_positions - matched_positions
                missing_ids = wanted_ids - matched_ids
                if missing_pos:
                    logger.warning(
                        "video_indices not found in playlist (playlist has %d entries): %s",
                        len(entries),
                        sorted(missing_pos),
                    )
                if missing_ids:
                    logger.warning(
                        "video_ids not found in playlist: %s",
                        sorted(missing_ids),
                    )

                entries = filtered
            else:
                # Range-based selection (original behaviour)
                start = playlist_config.start_index - 1  # convert to 0-based
                end = playlist_config.end_index  # None = all
                entries = entries[start:end]
                if playlist_config.max_videos:
                    entries = entries[: playlist_config.max_videos]

            if playlist_config.reverse:
                entries = list(reversed(entries))

            pl_progress.playlist_info = playlist_info
            pl_progress.total_videos = len(entries)
            pl_progress.status = PlaylistStatus.DOWNLOADING
            await _emit()

            results: List[PlaylistItemResult] = []
            downloaded_files: List[str] = []
            semaphore = asyncio.Semaphore(playlist_config.concurrency)

            async def _download_one(entry: PlaylistVideoInfo) -> PlaylistItemResult:
                """Download a single playlist entry, respecting the semaphore."""
                async with semaphore:
                    if cancel_event.is_set():
                        return PlaylistItemResult(
                            index=entry.playlist_index or 0,
                            video_info=entry,
                            success=False,
                            error="Cancelled",
                        )

                    # Per-video progress callback — update pl_progress and re-emit
                    async def _video_cb(vp: DownloadProgress) -> None:
                        pl_progress.current_video_progress = vp
                        if progress_callback:
                            await call_callback(progress_callback, pl_progress)

                    pl_progress.current_index = entry.playlist_index or 0
                    pl_progress.current_video = entry
                    pl_progress.current_video_progress = None
                    await _emit()

                    try:
                        filepath = await self.download(
                            entry.url,
                            item_config,
                            _video_cb,
                        )
                        pl_progress.completed_videos += 1
                        pl_progress._recalculate_percentage()
                        result = PlaylistItemResult(
                            index=entry.playlist_index or 0,
                            video_info=entry,
                            success=True,
                            filepath=str(filepath),
                        )
                    except DownloadGotCanceledError:
                        pl_progress.failed_videos += 1
                        pl_progress._recalculate_percentage()
                        result = PlaylistItemResult(
                            index=entry.playlist_index or 0,
                            video_info=entry,
                            success=False,
                            error="Cancelled",
                        )
                    except Exception as exc:
                        logger.warning(
                            "Playlist item %s failed: %s",
                            entry.url,
                            exc,
                        )
                        pl_progress.failed_videos += 1
                        pl_progress._recalculate_percentage()
                        result = PlaylistItemResult(
                            index=entry.playlist_index or 0,
                            video_info=entry,
                            success=False,
                            error=str(exc),
                        )
                        if not playlist_config.skip_on_error:
                            raise

                    pl_progress.results.append(result)
                    await _emit()
                    return result

            # --- Run downloads ---
            if playlist_config.concurrency == 1:
                # Sequential — simpler, friendlier for rate limits
                for entry in entries:
                    if cancel_event.is_set():
                        break
                    result = await _download_one(entry)
                    results.append(result)
                    if result.filepath:
                        downloaded_files.append(result.filepath)
            else:
                # Concurrent
                tasks = [asyncio.create_task(_download_one(e)) for e in entries]
                try:
                    done_results = await asyncio.gather(*tasks, return_exceptions=True)
                    for r in done_results:
                        if isinstance(r, PlaylistItemResult):
                            results.append(r)
                            if r.filepath:
                                downloaded_files.append(r.filepath)
                        elif (
                            isinstance(r, Exception)
                            and not playlist_config.skip_on_error
                        ):
                            raise r
                except asyncio.CancelledError:
                    for t in tasks:
                        t.cancel()
                    raise

            # Detect if cancelled
            was_cancelled = cancel_event.is_set()
            success = pl_progress.completed_videos > 0

            pl_progress.status = (
                PlaylistStatus.CANCELLED
                if was_cancelled
                else PlaylistStatus.COMPLETED if success else PlaylistStatus.FAILED
            )
            pl_progress.overall_percentage = (
                round(pl_progress.completed_videos / len(entries) * 100, 1)
                if entries
                else 100.0
            )
            await _emit()

            if was_cancelled:
                raise PlaylistCancelledError(
                    playlist_id,
                    pl_progress.completed_videos,
                    pl_progress.total_videos,
                )

            return PlaylistResponse(
                success=success,
                message=(
                    f"Downloaded {pl_progress.completed_videos} of "
                    f"{pl_progress.total_videos} videos"
                ),
                playlist_info=playlist_info,
                results=results,
                total_videos=pl_progress.total_videos,
                successful_downloads=pl_progress.completed_videos,
                failed_downloads=pl_progress.failed_videos,
                downloaded_files=downloaded_files,
            )

        except PlaylistCancelledError:
            raise
        except PlaylistDownloadError:
            raise
        except asyncio.CancelledError:
            raise PlaylistCancelledError(
                playlist_id,
                pl_progress.completed_videos,
                pl_progress.total_videos,
            )
        except Exception as exc:
            pl_progress.status = PlaylistStatus.FAILED
            if progress_callback:
                await call_callback(progress_callback, pl_progress)
            return PlaylistResponse(
                success=False,
                message="Playlist download failed",
                error=str(exc),
                total_videos=pl_progress.total_videos,
                successful_downloads=pl_progress.completed_videos,
                failed_downloads=pl_progress.failed_videos,
            )
        finally:
            self._playlist_cancel_events.pop(playlist_id, None)