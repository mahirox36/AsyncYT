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
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, List, Optional, Union
import aiofiles
import aiohttp
import logging

from asyncyt.exception import (
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
from .utils import call_callback, gen_id, get_unique_filename

logger = logging.getLogger(__name__)

__all__ = ["Downloader"]


class Downloader:
    """Main downloader class with async support"""

    def __init__(self):
        self.project_root = Path.cwd()
        self.bin_dir = self.project_root / "bin"
        system = platform.system().lower()

        self.ytdlp_path = (
            self.bin_dir / "yt-dlp.exe"
            if system == "windows"
            else self.bin_dir / "yt-dlp"
        )
        self.ffmpeg_path = (
            self.bin_dir / "ffmpeg.exe" if system == "windows" else "ffmpeg"
        )
        self._downloads: Dict[str, Process] = {}

    async def setup_binaries_generator(self) -> AsyncGenerator[SetupProgress, Any]:
        """Download and setup yt-dlp and ffmpeg binaries with yield SetupProgress"""
        self.bin_dir.mkdir(exist_ok=True)

        # Setup yt-dlp
        async for progress in self._setup_ytdlp():
            yield progress

        # Setup ffmpeg
        async for progress in self._setup_ffmpeg():
            yield progress

        logger.info("All binaries are ready!")

    async def setup_binaries(self) -> None:
        """Download and setup yt-dlp and ffmpeg binaries"""
        self.bin_dir.mkdir(exist_ok=True)

        # Setup yt-dlp
        async for _ in self._setup_ytdlp():
            pass

        # Setup ffmpeg
        async for _ in self._setup_ffmpeg():
            pass

        logger.info("All binaries are ready!")

    async def _setup_ytdlp(self) -> AsyncGenerator[SetupProgress, Any]:
        """Download yt-dlp binary"""
        system = platform.system().lower()

        if system == "windows":
            url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
        else:
            url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"

        if not self.ytdlp_path.exists():
            logger.info(f"Downloading yt-dlp...")
            async for progress in self._download_file(url, self.ytdlp_path):
                yield SetupProgress(file="yt-dlp", download_file_progress=progress)

            if system != "windows":
                os.chmod(self.ytdlp_path, 0o755)

    async def _setup_ffmpeg(self) -> AsyncGenerator[SetupProgress, Any]:
        """Download ffmpeg binary"""
        system = platform.system().lower()

        if system == "windows":
            self.ffmpeg_path = self.bin_dir / "ffmpeg.exe"

            if not self.ffmpeg_path.exists():
                logger.info(f"Downloading ffmpeg for Windows...")
                url = "https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-n7.1-latest-win64-lgpl-7.1.zip"
                temp_file = self.bin_dir / "ffmpeg.zip"

                async for progress in self._download_file(url, temp_file):
                    yield SetupProgress(file="ffmpeg", download_file_progress=progress)
                progress.status = "extracting"
                yield SetupProgress(file="ffmpeg", download_file_progress=progress)
                await self._extract_ffmpeg_windows(temp_file)
                temp_file.unlink()

        else:
            # For macOS, we'll check if ffmpeg is available via Homebrew
            if shutil.which("ffmpeg"):
                self.ffmpeg_path = "ffmpeg"
            else:
                logger.warning(
                    "ffmpeg not found. Please install via your package manager"
                )

    async def _extract_ffmpeg_windows(self, zip_path: Path) -> None:
        """Extract ffmpeg from Windows zip file"""
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            for file_info in zip_ref.infolist():
                if file_info.filename.endswith(("ffmpeg.exe", "ffprobe.exe")):
                    # Extract to bin directory
                    file_info.filename = os.path.basename(file_info.filename)
                    zip_ref.extract(file_info, self.bin_dir)

    async def _download_file(
        self, url: str, filepath: Path, max_retries: int = 5
    ) -> AsyncGenerator[DownloadFileProgress, Any]:
        """Download a file asynchronously with retries, timeout, resume support, and file size verification"""
        temp_filepath = filepath.with_suffix(filepath.suffix + ".part")
        attempt = 0
        backoff = 2
        while attempt < max_retries:
            try:
                resume_pos = 0
                if temp_filepath.exists():
                    resume_pos = temp_filepath.stat().st_size
                headers = {}
                if resume_pos > 0:
                    headers["Range"] = f"bytes={resume_pos}-"

                timeout_obj = aiohttp.ClientTimeout(
                    total=None, sock_connect=30, sock_read=60
                )
                async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                    async with session.get(url, headers=headers) as response:
                        if response.status in (200, 206):
                            mode = (
                                "ab"
                                if resume_pos > 0 and response.status == 206
                                else "wb"
                            )
                            async with aiofiles.open(temp_filepath, mode) as f:
                                downloaded = resume_pos
                                total = (
                                    int(response.headers.get("Content-Length", 0))
                                    + resume_pos
                                    if response.status == 206
                                    else int(response.headers.get("Content-Length", 0))
                                )
                                async for chunk in response.content.iter_chunked(8192):
                                    await f.write(chunk)
                                    downloaded += len(chunk)
                                    percent = (downloaded / total) * 100
                                    yield DownloadFileProgress(
                                        status="downloading",
                                        downloaded_bytes=downloaded,
                                        total_bytes=total,
                                        percentage=percent,
                                    )
                            # Verify file size
                            if total > 0 and temp_filepath.stat().st_size != total:
                                raise AsyncYTBase(
                                    f"Incomplete download for {filepath.name}: expected {total}, got {temp_filepath.stat().st_size}"
                                )
                            temp_filepath.rename(filepath)
                            return
                        else:
                            raise AsyncYTBase(
                                f"Failed to download {url}: {response.status}"
                            )
            except Exception as e:
                attempt += 1
                wait = backoff**attempt
                logger.warning(
                    f"Download attempt {attempt} failed for {url}: {e}. Retrying in {wait}s..."
                )
                await asyncio.sleep(wait)
        raise AsyncYTBase(f"Failed to download {url} after {max_retries} attempts.")

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

    async def search(self, query: str, max_results: int = 10) -> List[VideoInfo]:
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

    async def download(
        self,
        url: str,
        config: Optional[DownloadConfig] = None,
        progress_callback: Optional[
            Callable[[DownloadProgress], Union[None, Awaitable[None]]]
        ] = None,
    ) -> str:
        """Download a video with the given configuration"""
        if not config:
            config = DownloadConfig()
        id = gen_id(url, config)
        if id in self._downloads:
            raise DownloadAlreadyExistsError(id)

        # Ensure output directory exists
        output_dir = Path(config.output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build yt-dlp command
        cmd = await self._build_download_command(url, config)

        # Create progress tracker
        progress = DownloadProgress(url=url, percentage=0)

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

    async def health_check(self) -> HealthResponse:
        """Check if all binaries are available and working"""
        try:
            # Check yt-dlp
            ytdlp_available = False
            if self.ytdlp_path and self.ytdlp_path.exists():
                try:
                    process = await asyncio.create_subprocess_exec(
                        str(self.ytdlp_path),
                        "--version",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    await process.communicate()
                    ytdlp_available = process.returncode == 0
                except Exception:
                    ytdlp_available = False

            # Check ffmpeg
            ffmpeg_available = False
            if self.ffmpeg_path:
                try:
                    ffmpeg_cmd = (
                        str(self.ffmpeg_path)
                        if self.ffmpeg_path != "ffmpeg"
                        else "ffmpeg"
                    )
                    process = await asyncio.create_subprocess_exec(
                        ffmpeg_cmd,
                        "-version",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    await process.communicate()
                    ffmpeg_available = process.returncode == 0
                except Exception:
                    ffmpeg_available = False

            status = "healthy" if (ytdlp_available and ffmpeg_available) else "degraded"

            return HealthResponse(
                status=status,
                yt_dlp_available=ytdlp_available,
                ffmpeg_available=ffmpeg_available,
                binaries_path=str(self.bin_dir),
            )

        except Exception as e:
            return HealthResponse(
                status="unhealthy",
                yt_dlp_available=False,
                ffmpeg_available=False,
                error=str(e),
            )

    async def download_with_response(
        self,
        request: DownloadRequest,
        progress_callback: Optional[
            Callable[[DownloadProgress], Union[None, Awaitable[None]]]
        ] = None,
    ) -> DownloadResponse:
        """Download with API-friendly response format"""
        try:
            config = request.config or DownloadConfig()

            # Get video info first
            try:
                video_info = await self.get_video_info(request.url)
            except Exception as e:
                return DownloadResponse(
                    success=False,
                    message="Failed to get video information",
                    error=str(e),
                )

            # Download the video
            filename = await self.download(request.url, config, progress_callback)
            file = Path(filename)
            title = re.sub(r'[\\/:"*?<>|]', "_", video_info.title)
            new_file = get_unique_filename(file, title)
            file = file.rename(new_file)

            return DownloadResponse(
                success=True,
                message="Download completed successfully",
                filename=str(file.absolute()),
                video_info=video_info,
            )
        except AsyncYTBase:
            raise

        except Exception as e:
            return DownloadResponse(
                success=False, message="Download failed", error=str(e)
            )

    async def search_with_response(self, request: SearchRequest) -> SearchResponse:
        """Search with API-friendly response format"""
        try:
            results = await self.search(request.query, request.max_results)

            return SearchResponse(
                success=True,
                message=f"Found {len(results)} results",
                results=results,
                total_results=len(results),
            )

        except Exception as e:
            return SearchResponse(success=False, message="Search failed", error=str(e))

    async def download_playlist_with_response(
        self,
        request: PlaylistRequest,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
    ) -> PlaylistResponse:
        """Download playlist with API-friendly response format"""
        try:
            config = request.config or DownloadConfig()

            # Get playlist info
            playlist_info = await self.get_playlist_info(request.url)
            total_videos = min(len(playlist_info["entries"]), request.max_videos)

            downloaded_files = []
            failed_downloads = []

            for i, video_entry in enumerate(
                playlist_info["entries"][: request.max_videos]
            ):
                try:
                    if progress_callback:
                        overall_progress = DownloadProgress(
                            url=request.url,
                            title=f"Playlist item {i+1}/{total_videos}",
                            percentage=(i / total_videos) * 100,
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

    async def download_playlist(
        self,
        url: str,
        config: Optional[DownloadConfig] = None,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
    ) -> List[str]:
        """Download an entire playlist"""
        if not config:
            config = DownloadConfig()

        # Get playlist info first
        playlist_info = await self.get_playlist_info(url)
        downloaded_files = []

        for i, video_url in enumerate(playlist_info["entries"]):
            if progress_callback:
                overall_progress = DownloadProgress(
                    url=url,
                    title=f"Playlist item {i+1}/{len(playlist_info['entries'])}",
                    percentage=(i / len(playlist_info["entries"])) * 100,
                )
                progress_callback(overall_progress)

            try:
                filename = await self.download(
                    video_url["webpage_url"], config, progress_callback
                )
                downloaded_files.append(filename)
            except Exception as e:
                logger.error(
                    f"Failed to download {video_url.get('title', 'Unknown')}: {e}"
                )

        return downloaded_files

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

    async def _build_download_command(
        self, url: str, config: DownloadConfig
    ) -> List[str]:
        """Build the yt-dlp command based on configuration"""
        cmd = [str(self.ytdlp_path)]

        # Basic options
        cmd.extend(["--no-warnings", "--progress"])
        # Quality selection
        if config.extract_audio:
            audio = (
                AudioFormat(config.audio_format).value
                if config.audio_format
                else "best"
            )
            audio = (
                "vorbis" if audio == "ogg" else audio
            )  # Somehow it's not ogg but called vorbis??
            cmd.extend(
                [
                    "-x",
                    "--audio-format",
                    audio,
                ]
            )
        else:
            quality = Quality(config.quality)

            format_selector = ""

            if quality == Quality.BEST:
                format_selector = "bv*+ba/b"
            elif quality == Quality.WORST:
                format_selector = "worst"
            elif quality == Quality.AUDIO_ONLY:
                format_selector = "bestaudio"
            elif quality == Quality.VIDEO_ONLY:
                format_selector = "bestvideo"
            else:
                height = quality.value.replace("p", "")
                format_selector = (
                    f"bestvideo[height<={height}][ext=mp4]+"
                    f"bestaudio[ext=m4a]/best[height<={height}][ext=mp4]"
                )

            cmd.extend(["-f", format_selector])

        # Output format
        if config.video_format and not config.extract_audio:
            cmd.extend(["--recode-video", VideoFormat(config.video_format).value])

        # Filename template
        if config.custom_filename:
            cmd.extend(["-o", config.custom_filename])
        else:
            cmd.extend(["-o", "%(title)s.%(ext)s"])

        # Subtitles
        if config.write_subs:
            cmd.extend(["--write-subs", "--sub-lang", config.subtitle_lang])
        if config.embed_subs:
            cmd.append("--embed-subs")

        # Additional options
        if config.write_thumbnail:
            cmd.append("--write-thumbnail")
        if config.embed_thumbnail:
            cmd.append("--embed-thumbnail")
        if config.write_info_json:
            cmd.append("--write-info-json")
        if config.cookies_file:
            cmd.extend(["--cookies", config.cookies_file])
        if config.proxy:
            cmd.extend(["--proxy", config.proxy])
        if config.rate_limit:
            cmd.extend(["--limit-rate", config.rate_limit])
        if config.embed_metadata:
            cmd.append("--add-metadata")

        # Retry options
        cmd.extend(["--retries", str(config.retries)])
        cmd.extend(["--fragment-retries", str(config.fragment_retries)])

        # FFmpeg path
        if self.ffmpeg_path:
            cmd.extend(["--ffmpeg-location", str(self.ffmpeg_path)])

        # Custom options
        for key, value in config.custom_options.items():
            if isinstance(value, bool):
                if value:
                    cmd.append(f"--{key}")
            else:
                cmd.extend([f"--{key}", str(value)])

        cmd.extend(
            [
                "--progress-template",
                "download:PROGRESS|%(progress._percent_str)s|%(progress._downloaded_bytes_str)s|%(progress._total_bytes_str)s|%(progress._speed_str)s|%(progress._eta_str)s",
            ]
        )
        cmd.append("--no-update")
        cmd.append("--newline")
        cmd.append("--restrict-filenames")
        cmd.extend(["--print", "after_move:filepath"])

        cmd.append(url)
        return cmd

    async def _read_process_output(self, process):
        """Read process output line by line as UTF-8 (with replacement for bad chars)"""
        assert process.stdout is not None, "Process must have stdout=PIPE"

        while True:
            line = await process.stdout.readline()
            if not line:
                break
            yield line.decode("utf-8", errors="replace").rstrip()

    def _parse_progress(self, line: str, progress: DownloadProgress) -> None:
        """Parse progress information from yt-dlp output"""
        line = line.strip()
        if "Destination:" in line:
            # Extract title
            progress.title = Path(line.split("Destination: ")[1]).stem
            return

        if line.startswith("PROGRESS|"):
            try:
                # Split the custom format: PROGRESS|percentage|downloaded|total|speed|eta
                parts = line.split("|")
                if len(parts) >= 6:
                    percentage_str = parts[1].replace("%", "").strip()
                    downloaded_str = parts[2].strip()
                    total_str = parts[3].strip()
                    speed_str = parts[4].strip()
                    eta_str = parts[5].strip()

                    # Parse percentage
                    if percentage_str and percentage_str != "N/A":
                        progress.percentage = float(percentage_str)

                    # Parse downloaded bytes
                    if downloaded_str and downloaded_str != "N/A":
                        progress.downloaded_bytes = self._parse_size(downloaded_str)

                    # Parse total bytes
                    if total_str and total_str != "N/A":
                        progress.total_bytes = self._parse_size(total_str)

                    # Parse speed
                    if speed_str and speed_str != "N/A":
                        progress.speed = speed_str

                    # Parse ETA
                    if eta_str and eta_str != "N/A":
                        progress.eta = self._parse_time(eta_str)

                    return
            except (ValueError, IndexError) as e:
                pass

    def _parse_size(self, size_str: str) -> int:
        """Parse size string (e.g., '10.5MiB', '1.2GB') to bytes"""
        if not size_str:
            return 0

        size_str = size_str.strip().replace("~", "")

        # Handle different size units
        multipliers = {
            "B": 1,
            "KiB": 1024,
            "KB": 1000,
            "MiB": 1024**2,
            "MB": 1000**2,
            "GiB": 1024**3,
            "GB": 1000**3,
            "TiB": 1024**4,
            "TB": 1000**4,
        }

        for unit, multiplier in multipliers.items():
            if size_str.endswith(unit):
                try:
                    number = float(size_str[: -len(unit)])
                    return int(number * multiplier)
                except ValueError:
                    return 0

        # If no unit, assume bytes
        try:
            return int(float(size_str))
        except ValueError:
            return 0

    def _parse_time(self, time_str: str) -> int:
        """Parse time string to seconds"""
        try:
            parts = time_str.split(":")
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            else:
                return int(time_str)
        except ValueError:
            return 0
