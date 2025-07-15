"""
AsyncYT - A comprehensive async Any website downloader library
Uses yt-dlp and ffmpeg with automatic binary management
"""

import asyncio
from asyncio.subprocess import Process
import json
import os
import platform
import re
import shutil
import zipfile
from pathlib import Path
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Union,
    overload,
)
from collections.abc import Callable as Callable2
import aiofiles
import aiohttp
import logging

from asyncyt.exceptions import (
    AsyncYTBase,
    DownloadAlreadyExistsError,
    DownloadGotCanceledError,
    DownloadNotFoundError,
    YtdlpDownloadError,
    YtdlpGetInfoError,
    YtdlpPlaylistGetInfoError,
    YtdlpSearchError,
)

from .enums import AudioFormat, VideoFormat, Quality
from .basemodels import (
    DownloadFileProgress,
    SetupProgress,
    VideoInfo,
    DownloadConfig,
    DownloadProgress,
    DownloadRequest,
    SearchRequest,
    PlaylistRequest,
    DownloadResponse,
    SearchResponse,
    PlaylistResponse,
    HealthResponse,
)
from .utils import call_callback, get_id, get_unique_filename
from .binaries import BinaryManager

logger = logging.getLogger(__name__)

__all__ = ["Downloader"]


class Downloader(BinaryManager):
    """Main downloader class with async support"""

    def __init__(self):
        super().__init__()
        self._downloads: Dict[str, Process] = {}

    async def get_video_info(self, url: str) -> VideoInfo:
        """Get video information without downloading"""
        cmd = [str(self.ytdlp_path), "--dump-json", "--no-warnings", url]

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise YtdlpGetInfoError(url, process.returncode, stderr.decode())

        data = json.loads(stdout.decode())
        return VideoInfo.from_dict(data)

    async def _search(self, query: str, max_results: int = 10) -> List[VideoInfo]:
        """Search for videos"""
        search_url = f"ytsearch{max_results}:{query}"

        cmd = [str(self.ytdlp_path), "--dump-json", "--no-warnings", search_url]

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise YtdlpSearchError(query, process.returncode, stderr.decode())

        results = []
        for line in stdout.decode().strip().split("\n"):
            if line:
                data = json.loads(line)
                results.append(VideoInfo.from_dict(data))

        return results

    def _get_config(
        self,
        *args,
        **kwargs: Dict[
            str,
            Union[
                str,
                Optional[DownloadConfig],
                Optional[Callable[[DownloadProgress], Union[None, Awaitable[None]]]],
            ],
        ],
    ):
        url: Optional[str] = None
        config: Optional[DownloadConfig] = None
        progress_callback: Optional[
            Callable[[DownloadProgress], Union[None, Awaitable[None]]]
        ] = None
        if "url" in kwargs:
            url = kwargs.get("url")  # type: ignore
            if not isinstance(url, str):
                raise TypeError("url must be str!")
        if "config" in kwargs:
            config = kwargs.get("config")  # type: ignore
            if not isinstance(config, DownloadConfig):
                raise TypeError("config must be DownloadConfig!")
        if "progress_callback" in kwargs:
            progress_callback = kwargs.get("progress_callback")  # type: ignore
            if not isinstance(progress_callback, Callable2):
                raise TypeError("progress_callback must be callable!")
        if "request" in kwargs:
            request = kwargs.get("request")
            if not isinstance(request, DownloadRequest):
                raise TypeError("request must be DownloadRequest!")
            url = request.url
            config = request.config
        for arg in args:
            if isinstance(arg, str):
                url = arg
            elif isinstance(arg, DownloadConfig):
                config = arg
            elif isinstance(arg, Callable):
                progress_callback = arg
            elif isinstance(arg, DownloadRequest):
                url = arg.url
                config = arg.config
        if not url:
            raise TypeError("url is a must!")

        return (url, config, progress_callback)

    @overload
    async def download(
        self,
        url: str,
        config: Optional[DownloadConfig] = None,
        progress_callback: Optional[
            Callable[[DownloadProgress], Union[None, Awaitable[None]]]
        ] = None,
    ) -> str: ...
    @overload
    async def download(
        self,
        request: DownloadRequest,
        progress_callback: Optional[
            Callable[[DownloadProgress], Union[None, Awaitable[None]]]
        ] = None,
    ) -> str: ...

    async def download(self, *args, **kwargs) -> str:
        """Download a video with the given configuration"""
        url, config, progress_callback = self._get_config(*args, **kwargs)
        if not config:
            config = DownloadConfig()
        id = get_id(url, config)
        if id in self._downloads:
            raise DownloadAlreadyExistsError(id)

        # Ensure output directory exists
        output_dir = Path(config.output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build yt-dlp command
        cmd = await self._build_download_command(url, config)

        # Create progress tracker
        progress = DownloadProgress(url=url, percentage=0, id=id)

        # Execute download
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=output_dir,
        )

        self._downloads[id] = process

        output_file: Optional[str] = None

        output: List[str] = []
        # Monitor progress
        async for line in self._read_process_output(process):
            line = line.strip()
            output.append(line)

            if line:
                old_percentage = progress.percentage
                self._parse_progress(line, progress)

                if progress_callback and progress.percentage > old_percentage:
                    await call_callback(progress_callback, progress)

                # Robust output filename extraction: only set if line is an absolute path, has a valid extension, and file exists
                valid_exts = (
                    ".mp3",
                    ".m4a",
                    ".wav",
                    ".flac",
                    ".ogg",
                    ".wav",
                    ".mp4",
                    ".webm",
                    ".mkv",
                    ".avi",
                    ".opus",
                    ".aac",
                )
                if not output_file and line.lower().endswith(valid_exts):
                    output_file = line
        try:
            returncode = await process.wait()

            if returncode != 0:
                raise YtdlpDownloadError(
                    url=url, output=output, cmd=cmd, error_code=returncode
                )

            if progress_callback:
                progress.status = "finished"
                progress.percentage = 100.0
                await call_callback(progress_callback, progress)
            return output_file  # type: ignore
        except asyncio.CancelledError:
            process.kill()
            await process.wait()
            raise DownloadGotCanceledError(id)
        finally:
            self._downloads.pop(id, None)

    async def cancel(self, download_id: str):
        """cancel the downloading with download_id"""
        process = self._downloads.pop(download_id, None)
        if not process:
            raise DownloadNotFoundError(download_id)
        process.kill()
        await process.wait()

    @overload
    async def download_with_response(
        self,
        url: str,
        config: Optional[DownloadConfig] = None,
        progress_callback: Optional[
            Callable[[DownloadProgress], Union[None, Awaitable[None]]]
        ] = None,
    ) -> DownloadResponse: ...
    @overload
    async def download_with_response(
        self,
        request: DownloadRequest,
        progress_callback: Optional[
            Callable[[DownloadProgress], Union[None, Awaitable[None]]]
        ] = None,
    ) -> DownloadResponse: ...

    async def download_with_response(self, *args, **kwargs) -> DownloadResponse:
        """Download with API-friendly response format"""
        try:
            url, config, progress_callback = self._get_config(*args, **kwargs)
            config = config or DownloadConfig()
            id = get_id(url, config)

            # Get video info first
            try:
                video_info = await self.get_video_info(url)
            except YtdlpGetInfoError as e:
                return DownloadResponse(
                    success=False,
                    message="Failed to get video information",
                    error=f"error code: {e.error_code}\nOutput: {e.output}",
                    id=id,
                )
            except Exception as e:
                return DownloadResponse(
                    success=False,
                    message="Failed to get video information",
                    error=str(e),
                    id=id,
                )

            # Download the video
            filename = await self.download(url, config, progress_callback)
            file = Path(filename)
            title = re.sub(r'[\\/:"*?<>|]', "_", video_info.title)
            new_file = get_unique_filename(file, title)
            file = file.rename(new_file)

            return DownloadResponse(
                success=True,
                message="Download completed successfully",
                filename=str(file.absolute()),
                video_info=video_info,
                id=id,
            )
        except AsyncYTBase:
            raise

        except Exception as e:
            return DownloadResponse(
                success=False, message="Download failed", error=str(e), id=id
            )

    @overload
    async def search(self, query: str, max_results: Optional[int] = None) -> "SearchResponse": ...

    @overload
    async def search(self, *, request: "SearchRequest") -> "SearchResponse": ...

    async def search(
        self,
        query: Optional[str] = None,
        max_results: Optional[int] = None,
        *,
        request: Optional["SearchRequest"] = None,
    ) -> SearchResponse:
        """Search with API-friendly response format"""

        if request is not None:
            if query is not None or max_results is not None:
                raise TypeError("If you provide request, you cannot provide query, or max_results.")
        else:
            if query is None:
                raise TypeError("You must provide query when request is not given.")

        if request:
            query = request.query
            max_results = request.max_results
        if max_results is None:
            max_results = 10

        try:
            results = await self._search(query, max_results)  # type: ignore

            return SearchResponse(
                success=True,
                message=f"Found {len(results)} results",
                results=results,
                total_results=len(results),
            )

        except Exception as e:
            return SearchResponse(success=False, message="Search failed", error=str(e))

    @overload
    async def download_playlist(
        self,
        url: str,
        config: Optional[DownloadConfig] = None,
        max_videos: Optional[int] = None,
        progress_callback: Optional[
            Callable[[DownloadProgress], Union[None, Awaitable[None]]]
        ] = None,
    ) -> PlaylistResponse: ...

    @overload
    async def download_playlist(
        self,
        *,
        request: PlaylistRequest,
        progress_callback: Optional[
            Callable[[DownloadProgress], Union[None, Awaitable[None]]]
        ] = None,
    ) -> PlaylistResponse: ...

    async def download_playlist(
        self,
        url: Optional[str] = None,
        config: Optional[DownloadConfig] = None,
        max_videos: Optional[int] = None,
        progress_callback: Optional[
            Callable[[DownloadProgress], Union[None, Awaitable[None]]]
        ] = None,
        request: Optional[PlaylistRequest] = None,
    ) -> PlaylistResponse:
        """Download playlist with API-friendly response format"""
        if request is not None:
            if url is not None or config is not None or max_videos is not None:
                raise TypeError("If you provide request, you cannot provide url, config, or max_videos.")
        else:
            if url is None:
                raise TypeError("You must provide url when request is not given.")

        if request:
            url = request.url
            config = request.config
            max_videos = request.max_videos
        if not max_videos:
            max_videos = 100
        if not url:
            raise TypeError("the URL is must.")  # even tho it will not be ever raised
        try:
            config = config or DownloadConfig()
            id = get_id(url, config)

            # Get playlist info
            playlist_info = await self.get_playlist_info(url)
            total_videos = min(len(playlist_info["entries"]), max_videos)

            downloaded_files = []
            failed_downloads = []

            for i, video_entry in enumerate(playlist_info["entries"][:max_videos]):
                try:
                    if progress_callback:
                        overall_progress = DownloadProgress(
                            url=url,
                            title=f"Playlist item {i+1}/{total_videos}",
                            percentage=(i / total_videos) * 100,
                            id=id,
                        )
                        progress_callback(overall_progress)

                    filename = await self.download(video_entry["webpage_url"], config)
                    downloaded_files.append(filename)

                except Exception as e:
                    failed_downloads.append(
                        f"{video_entry.get('title', 'Unknown')}: {str(e)}"
                    )

            return PlaylistResponse(
                success=True,
                message=f"Downloaded {len(downloaded_files)} out of {total_videos} videos",
                downloaded_files=downloaded_files,
                failed_downloads=failed_downloads,
                total_videos=total_videos,
                successful_downloads=len(downloaded_files),
            )

        except Exception as e:
            return PlaylistResponse(
                success=False,
                message="Playlist download failed",
                error=str(e),
                total_videos=0,
                successful_downloads=0,
            )

    async def get_playlist_info(self, url: str) -> Dict[str, Any]:
        """Get playlist information"""
        cmd = [
            str(self.ytdlp_path),
            "--dump-json",
            "--flat-playlist",
            "--no-warnings",
            url,
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise YtdlpPlaylistGetInfoError(url, process.returncode, stderr.decode())

        entries = []
        for line in stdout.decode().strip().split("\n"):
            if line:
                entries.append(json.loads(line))

        return {
            "entries": entries,
            "title": (
                entries[0].get("playlist_title", "Unknown Playlist")
                if entries
                else "Empty Playlist"
            ),
        }

    # TODO: Add Cancel Function for playlist
    # TODO: also add basemodel for just the playlist downloading and the get_playlist_info
