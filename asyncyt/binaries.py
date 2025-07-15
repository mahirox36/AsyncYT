"""
AsyncYT - A comprehensive async Any website downloader library
Uses yt-dlp and ffmpeg with automatic binary management
"""

import asyncio
import os
import platform
import shutil
import zipfile
from pathlib import Path
from typing import (
    Any,
    AsyncGenerator,
    List,
)
import aiofiles
import aiohttp
import logging

from asyncyt.basemodels import (
    DownloadConfig,
    DownloadFileProgress,
    DownloadProgress,
    HealthResponse,
    SetupProgress,
)
from asyncyt.enums import AudioFormat, Quality, VideoFormat
from asyncyt.exceptions import (
    AsyncYTBase,
)

logger = logging.getLogger(__name__)

__all__ = ["BinaryManager"]


class BinaryManager:
    """Main Manager For managing binaries"""

    def __init__(self):
        self.bin_dir = Path.cwd() / "bin"
        system = platform.system().lower()

        self.ytdlp_path = (
            self.bin_dir / "yt-dlp.exe"
            if system == "windows"
            else self.bin_dir / "yt-dlp"
        )
        self.ffmpeg_path = (
            self.bin_dir / "ffmpeg.exe" if system == "windows" else "ffmpeg"
        )

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
                    total=None, sock_connect=30, sock_read=300
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
                                chunk_size = 4096

                                async for chunk in response.content.iter_chunked(
                                    chunk_size
                                ):
                                    await f.write(chunk)
                                    downloaded += len(chunk)

                                    # Calculate progress
                                    if total > 0:
                                        percent = (downloaded / total) * 100
                                    else:
                                        percent = 0

                                    yield DownloadFileProgress(
                                        status="downloading",
                                        downloaded_bytes=downloaded,
                                        total_bytes=total,
                                        percentage=percent,
                                    )

                            # Verify file size (only if we know the expected size)
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
            except asyncio.TimeoutError as e:
                attempt += 1
                wait = min(backoff**attempt, 60)  # Cap wait time at 60 seconds
                logger.warning(
                    f"Download attempt {attempt} timed out for {url}: {e}. Retrying in {wait}s..."
                )
                await asyncio.sleep(wait)

            except Exception as e:
                attempt += 1
                wait = min(backoff**attempt, 60)  # Cap wait time at 60 seconds
                logger.warning(
                    f"Download attempt {attempt} failed for {url}: {e}. Retrying in {wait}s..."
                )
                await asyncio.sleep(wait)

        raise AsyncYTBase(f"Failed to download {url} after {max_retries} attempts.")

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
