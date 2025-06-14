"""
AsyncYT - A comprehensive async YouTube downloader library
Uses yt-dlp and ffmpeg with automatic binary management
"""

import asyncio
import json
import os
import platform
import shutil
import zipfile
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union
import aiofiles
import aiohttp

from .enums import AudioFormat, VideoFormat, Quality
from .basemodels import (
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
from .utils import call_callback

class Downloader:
    """Main downloader class with async support"""

    def __init__(self):
        self.project_root = Path.cwd()
        self.bin_dir = self.project_root / "bin"
        self.ytdlp_path = None
        self.ffmpeg_path = None
        self.ffprobe_path = None

    async def setup_binaries(self) -> None:
        """Download and setup yt-dlp and ffmpeg binaries"""
        self.bin_dir.mkdir(exist_ok=True)

        # Setup yt-dlp
        await self._setup_ytdlp()

        # Setup ffmpeg
        await self._setup_ffmpeg()

        print("✅ All binaries are ready!")

    async def _setup_ytdlp(self) -> None:
        """Download yt-dlp binary"""
        system = platform.system().lower()

        if system == "windows":
            filename = "yt-dlp.exe"
            url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
        else:
            filename = "yt-dlp"
            url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"

        self.ytdlp_path = self.bin_dir / filename

        if not self.ytdlp_path.exists():
            print(f"📥 Downloading yt-dlp...")
            await self._download_file(url, self.ytdlp_path)

            if system != "windows":
                os.chmod(self.ytdlp_path, 0o755)

    async def _setup_ffmpeg(self) -> None:
        """Download ffmpeg binary"""
        system = platform.system().lower()

        if system == "windows":
            self.ffmpeg_path = self.bin_dir / "ffmpeg.exe"
            self.ffprobe_path = self.bin_dir / "ffprobe.exe"

            if not self.ffmpeg_path.exists():
                print(f"📥 Downloading ffmpeg for Windows...")
                url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
                temp_file = self.bin_dir / "ffmpeg.zip"

                await self._download_file(url, temp_file)
                await self._extract_ffmpeg_windows(temp_file)
                temp_file.unlink()

        elif system == "darwin":  # macOS
            # For macOS, we'll check if ffmpeg is available via Homebrew
            if shutil.which("ffmpeg"):
                self.ffmpeg_path = "ffmpeg"
                self.ffprobe_path = "ffprobe"
            else:
                print("⚠️  ffmpeg not found. Please install via: brew install ffmpeg")

        else:  # Linux
            if shutil.which("ffmpeg"):
                self.ffmpeg_path = "ffmpeg"
                self.ffprobe_path = "ffprobe"
            else:
                print("⚠️  ffmpeg not found. Please install via your package manager")

    async def _extract_ffmpeg_windows(self, zip_path: Path) -> None:
        """Extract ffmpeg from Windows zip file"""
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            for file_info in zip_ref.infolist():
                if file_info.filename.endswith(("ffmpeg.exe", "ffprobe.exe")):
                    # Extract to bin directory
                    file_info.filename = os.path.basename(file_info.filename)
                    zip_ref.extract(file_info, self.bin_dir)

    async def _download_file(self, url: str, filepath: Path) -> None:
        """Download a file asynchronously"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    async with aiofiles.open(filepath, "wb") as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                else:
                    raise Exception(f"Failed to download {url}: {response.status}")

    async def get_video_info(self, url: str) -> VideoInfo:
        """Get video information without downloading"""
        cmd = [str(self.ytdlp_path), "--dump-json", "--no-warnings", url]

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(f"Failed to get video info: {stderr.decode()}")

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
            raise Exception(f"Search failed: {stderr.decode()}")

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
            config = DownloadConfig()  # type: ignore

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

        output_file: str

        # Monitor progress
        async for line in self._read_process_output(process):
            line = line.strip()

            if progress_callback:
                self._parse_progress(line, progress)
                await call_callback(progress_callback, progress)

            # Capture output filename
            if "[download] Destination:" in line:
                output_file: str = line.split("Destination: ")[1]
            elif "[download]" in line and "has already been downloaded" in line:
                output_file: str = line.split()[1]

        await process.wait()

        if process.returncode != 0:
            raise Exception(f"Download failed for {url}")

        if progress_callback:
            progress.status = "finished"
            progress.percentage = 100.0
            await call_callback(progress_callback, progress)
        return output_file

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
            config = request.config or DownloadConfig()  # type: ignore

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

            return DownloadResponse(
                success=True,
                message="Download completed successfully",
                filename=filename,
                video_info=video_info,
            )

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
            config = request.config or DownloadConfig()  # type: ignore

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
            config = DownloadConfig()  # type: ignore

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
                print(f"Failed to download {video_url.get('title', 'Unknown')}: {e}")

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
            raise Exception(f"Failed to get playlist info: {stderr.decode()}")

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
            cmd.extend(
                [
                    "-x",
                    "--audio-format",
                    (
                        AudioFormat(config.audio_format).value
                        if config.audio_format
                        else "mp3"
                    ),
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

        cmd.append(url)
        print(cmd)
        return cmd

    async def _read_process_output(self, process):
        """Read process output line by line"""
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            yield line.decode("utf-8", errors="ignore")

    def _parse_progress(self, line: str, progress: DownloadProgress) -> None:
        """Parse progress information from yt-dlp output"""
        line = line.strip()

        if "Destination:" in line:
            # Extract title
            progress.title = Path(line.split("Destination: ")[1]).stem
            return

        if "[download]" in line and "%" in line:
            try:
                # Clean line from carriage returns
                line = line.replace("\r", "").replace("\n", "")
                parts = line.split()

                for i, part in enumerate(parts):
                    if "%" in part:
                        progress.percentage = float(part.replace("%", "").strip())
                    elif part == "of" and i + 1 < len(parts):
                        progress.total_bytes = self._parse_size(parts[i + 1])
                    elif part == "at" and i + 1 < len(parts):
                        progress.speed = self._parse_speed(parts[i + 1])
                    elif part == "ETA" and i + 1 < len(parts):
                        progress.eta = self._parse_time(parts[i + 1])
            except (ValueError, IndexError):
                pass

    def _parse_size(self, size_str: str) -> int:
        """Parse size string to bytes"""
        try:
            size_str = size_str.upper()
            if "K" in size_str:
                return int(float(size_str.replace("K", "")) * 1024)
            elif "M" in size_str:
                return int(float(size_str.replace("M", "")) * 1024 * 1024)
            elif "G" in size_str:
                return int(float(size_str.replace("G", "")) * 1024 * 1024 * 1024)
            else:
                return int(size_str)
        except ValueError:
            return 0

    def _parse_speed(self, speed_str: str) -> float:
        """Parse speed string to bytes per second"""
        try:
            speed_str = speed_str.upper().replace("/S", "")
            if "K" in speed_str:
                return float(speed_str.replace("K", "")) * 1024
            elif "M" in speed_str:
                return float(speed_str.replace("M", "")) * 1024 * 1024
            elif "G" in speed_str:
                return float(speed_str.replace("G", "")) * 1024 * 1024 * 1024
            else:
                return float(speed_str)
        except ValueError:
            return 0.0

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
