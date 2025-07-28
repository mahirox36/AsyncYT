"""
AsyncYT - A comprehensive async Any website downloader library
Uses yt-dlp and ffmpeg with automatic binary management
"""

import asyncio
from asyncio.subprocess import Process
from json import loads
import os
import re
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union, overload
from collections.abc import Callable as Callable2
import logging
import warnings

from .enums import ProgressStatus, VideoFormat
from .exceptions import *
from .basemodels import *
from .utils import (
    call_callback,
    get_id,
    get_unique_filename,
)
from .binaries import AsyncFFmpeg

logger = logging.getLogger(__name__)

__all__ = ["AsyncYT", "Downloader"]


class AsyncYT(AsyncFFmpeg):
    """Main downloader class with async support"""

    def __init__(self):
        super().__init__()

    async def get_video_info(self, url: str) -> VideoInfo:
        """
        Asynchronously retrieves video information from a given URL using yt-dlp.
        Args:
            url (str): The URL of the video to retrieve information for.
        Returns:
            VideoInfo: An object containing the video's metadata.
        Raises:
            YtdlpGetInfoError: If yt-dlp fails to retrieve video information.
        """

        cmd = [str(self.ytdlp_path), "--dump-json", "--no-warnings", url]

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise YtdlpGetInfoError(url, process.returncode, stderr.decode())

        data = loads(stdout.decode())
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
                data = loads(line)
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
        """
        Asynchronously downloads media from a given URL using yt-dlp, tracks progress, and processes the output file.
        Args:
            url (str) or request (DownloadRequest): The URL or request object for the download.
            config (Optional[DownloadConfig]): Download configuration.
            progress_callback (Optional[Callable[[DownloadProgress], Union[None, Awaitable[None]]]]): Progress callback.
        Returns:
            str: The path to the processed output file.
        Raises:
            DownloadAlreadyExistsError: If a download with the same ID is already in progress.
            YtdlpDownloadError: If yt-dlp returns a non-zero exit code.
            Exception: If the output file cannot be determined from yt-dlp output.
            DownloadGotCanceledError: If the download is cancelled.
            FileNotFoundError: If FFmpeg wasn't installed.
        Side Effects:
            - Creates the output directory if it does not exist.
            - Tracks download progress and invokes the progress callback if provided.
            - Cleans up the download process from the internal tracking dictionary.
        """

        url, config, progress_callback = self._get_config(*args, **kwargs)
        if not config:
            config = DownloadConfig()

        id = get_id(url, config)
        if id in self._downloads:
            raise DownloadAlreadyExistsError(id)

        # Ensure output directory exists
        output_dir = Path(config.output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        if not self.ffmpeg_path:
            raise FileNotFoundError("FFmpeg isn't installed")

        config.ffmpeg_config.ffmpeg_path = str(self.ffmpeg_path)
        _original_embed_thumbnail = config.embed_thumbnail
        _original_write_thumbnail = config.write_thumbnail
        if config.embed_thumbnail:
            config.embed_thumbnail = False
            config.write_thumbnail = True

        # Build yt-dlp command
        cmd = await self._build_download_command(url, config)

        # Create progress tracker
        progress = DownloadProgress(url=url, percentage=0, id=id)

        output_file: Optional[str] = None  # Initialize properly

        try:
            # Execute download
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=output_dir,
            )

            self._downloads[id] = process
            output: List[str] = []

            # Monitor yt-dlp progress
            async for line in self._read_process_output(process):
                line = line.strip()
                output.append(line)

                if line:
                    old_percentage = progress.percentage
                    self._parse_progress(line, progress)

                    if progress_callback and progress.percentage > old_percentage:
                        await call_callback(progress_callback, progress)

                    # Robust output filename extraction
                    valid_exts = (
                        # Audio
                        ".mp3",
                        ".m4a",
                        ".wav",
                        ".flac",
                        ".ogg",
                        ".opus",
                        ".aac",
                        # Video
                        ".mp4",
                        ".webm",
                        ".mkv",
                        ".avi",
                        ".flv",
                        ".mov",
                    )
                    if not output_file and line.lower().endswith(valid_exts):
                        # Verify the file actually exists and is an absolute path
                        if os.path.isabs(line) and os.path.exists(line):
                            output_file = line

            returncode = await process.wait()

            if returncode != 0:
                raise YtdlpDownloadError(
                    url=url, output=output, cmd=cmd, error_code=returncode
                )

            if not output_file:
                raise Exception("Could not determine output file from yt-dlp")

            if progress_callback:
                progress.status = ProgressStatus.DOWNLOADED
                progress.percentage = 100.0
                await call_callback(progress_callback, progress)

            config.embed_thumbnail = _original_embed_thumbnail
            config.write_thumbnail = _original_write_thumbnail

            result = await self.process(
                output_file,
                config.ffmpeg_config,
                config,
                progress_callback,
                progress,
                url,
            )

            return result

        except asyncio.CancelledError:
            if id in self._downloads:
                process = self._downloads[id]
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
    async def search(
        self, query: str, max_results: Optional[int] = None
    ) -> "SearchResponse": ...

    @overload
    async def search(self, *, request: "SearchRequest") -> "SearchResponse": ...

    async def search(
        self,
        query: Optional[str] = None,
        max_results: Optional[int] = None,
        *,
        request: Optional["SearchRequest"] = None,
    ) -> SearchResponse:
        """
        Perform an asynchronous search operation.
        Args:
            query (Optional[str], optional): The search query string. Required if `request` is not provided.
            max_results (Optional[int], optional): The maximum number of results to return. Defaults to 10 if not specified.
            request (Optional["SearchRequest"], optional): An optional SearchRequest object containing search parameters.
                If provided, `query` and `max_results` must not be specified.
        Returns:
            SearchResponse: An object containing the search results, success status, message, and error (if any).
        Raises:
            TypeError: If both `request` and either `query` or `max_results` are provided, or if neither `request` nor `query` is provided.
        """

        if request is not None:
            if query is not None or max_results is not None:
                raise TypeError(
                    "If you provide request, you cannot provide query, or max_results."
                )
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
        """
        Asynchronously downloads videos from a YouTube playlist.
        You can provide either a `request` object containing all parameters, or specify
        `url`, `config`, and `max_videos` individually. If `request` is provided, you must
        not provide `url`, `config`, or `max_videos`.
        Args:
            url (Optional[str]): The URL of the playlist to download. Required if `request` is not given.
            config (Optional[DownloadConfig]): Download configuration options.
            max_videos (Optional[int]): Maximum number of videos to download from the playlist. Defaults to 100.
            progress_callback (Optional[Callable[[DownloadProgress], Union[None, Awaitable[None]]]]):
                Optional callback to report download progress.
            request (Optional[PlaylistRequest]): An object containing all playlist download parameters.
        Returns:
            PlaylistResponse: An object containing the result of the playlist download, including
                success status, message, list of downloaded files, failed downloads, total videos,
                and number of successful downloads.
        Raises:
            TypeError: If both `request` and any of `url`, `config`, or `max_videos` are provided,
                or if neither `request` nor `url` is provided.
        """
        if request is not None:
            if url is not None or config is not None or max_videos is not None:
                raise TypeError(
                    "If you provide request, you cannot provide url, config, or max_videos."
                )
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
        """
        Asynchronously retrieves information about a YouTube playlist using yt-dlp.
        Args:
            url (str): The URL of the YouTube playlist.
        Returns:
            Dict[str, Any]: A dictionary containing:
                - "entries": A list of video entries in the playlist, each as a dict.
                - "title": The title of the playlist, or "Unknown Playlist"/"Empty Playlist" if not available.
        Raises:
            YtdlpPlaylistGetInfoError: If the yt-dlp process fails to retrieve playlist information.
        """

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
                entries.append(loads(line))

        return {
            "entries": entries,
            "title": (
                entries[0].get("playlist_title", "Unknown Playlist")
                if entries
                else "Empty Playlist"
            ),
        }

    # TODO: also add basemodel for just the playlist downloading and the get_playlist_info


class DeprecatedDownloader(AsyncYT):

    @warnings.deprecated(
        "`Downloader` is deprecated; use `AsyncYT` instead.",
        category=DeprecationWarning,
    )
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Downloader is deprecated and will be removed in a future release. "
            "Please use AsyncYT instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)


Downloader = DeprecatedDownloader
