"""
AsyncYT - A comprehensive async Any website downloader library
Uses yt-dlp and ffmpeg with automatic binary management
"""

import asyncio
from asyncio.subprocess import Process
from collections.abc import Callable
from json import loads
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
    Dict,
    List,
    Optional,
    Union,
)
import aiofiles
import aiohttp
import logging

from ._version import __version__

from .utils import (
    call_callback,
    delete_file,
    get_id,
    get_unique_path,
    is_compatible,
    suggest_compatible_formats,
)
from .basemodels import *
from .enums import *
from .exceptions import (
    AsyncYTBase,
    CodecCompatibilityError,
    FFmpegOutputExistsError,
    FFmpegProcessingError,
)

logger = logging.getLogger(__name__)

__all__ = ["BinaryManager", "AsyncFFmpeg"]


class BinaryManager:
    """
    Main Manager for managing binaries.

    :param bin_dir: Directory for binary files (yt-dlp, ffmpeg).
    :type bin_dir: Optional[str | Path]
    """

    def __init__(self, bin_dir: Optional[str | Path] = None):
        if isinstance(bin_dir, str):
            bin_dir = Path(bin_dir)

        if bin_dir and bin_dir.exists() and not bin_dir.is_dir():
            raise ValueError(f"Path {bin_dir} not dir!")
        self.bin_dir = bin_dir or Path.cwd() / "bin"
        system = platform.system().lower()

        self.ytdlp_path = (
            self.bin_dir / "yt-dlp.exe"
            if system == "windows"
            else self.bin_dir / "yt-dlp"
        )
        self.ffmpeg_path = (
            self.bin_dir / "ffmpeg.exe" if system == "windows" else "ffmpeg"
        )
        self.ffprobe_path = (
            self.bin_dir / "ffprobe.exe" if system == "windows" else "ffprobe"
        )
        self._downloads: Dict[str, Process] = {}
        self._setup_only_ffmpeg: bool = False

    async def setup_binaries_generator(self) -> AsyncGenerator[SetupProgress, Any]:
        """
        Download and setup yt-dlp and ffmpeg binaries, yielding SetupProgress.

        :return: Async generator yielding SetupProgress objects.
        :rtype: AsyncGenerator[SetupProgress, Any]
        """
        self.bin_dir.mkdir(exist_ok=True)

        # Setup yt-dlp
        if not self._setup_only_ffmpeg:
            async for progress in self._setup_ytdlp():
                yield progress

        # Setup ffmpeg
        async for progress in self._setup_ffmpeg():
            yield progress

        logger.info("All binaries are ready!")

    async def setup_binaries(self) -> None:
        """
        Download and setup yt-dlp and ffmpeg binaries.

        :return: None
        """
        self.bin_dir.mkdir(exist_ok=True)

        # Setup yt-dlp
        if not self._setup_only_ffmpeg:
            async for _ in self._setup_ytdlp():
                pass

        # Setup ffmpeg
        async for _ in self._setup_ffmpeg():
            pass

        logger.info("All binaries are ready!")

    async def _setup_ytdlp(self) -> AsyncGenerator[SetupProgress, Any]:
        """
        Ensure yt-dlp binary is available and up-to-date.

        :return: Async generator yielding SetupProgress objects.
        """
        system = platform.system().lower()
        
        if system == "windows":
            url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
        else:
            url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"

        if self.ytdlp_path.exists():
            yield SetupProgress(
                file="yt-dlp",
                download_file_progress=DownloadFileProgress(
                    status=ProgressStatus.UPDATING,
                    downloaded_bytes=0,
                    total_bytes=0,
                    percentage=0,
                ),
            )

            try:
                process = await asyncio.create_subprocess_exec(
                    str(self.ytdlp_path),
                    "--update",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await process.communicate()

                if process.returncode != 0:
                    logger.warning(f"yt-dlp update failed: {stderr.decode().strip()}")

                yield SetupProgress(
                    file="yt-dlp",
                    download_file_progress=DownloadFileProgress(
                        status=ProgressStatus.COMPLETED,
                        downloaded_bytes=0,
                        total_bytes=0,
                        percentage=100,
                    ),
                )
            except Exception as e:
                logger.warning(f"yt-dlp update encountered an error: {e}")

        else:
            logger.info("Downloading yt-dlp...")
            async for progress in self._download_file(url, self.ytdlp_path):
                yield SetupProgress(file="yt-dlp", download_file_progress=progress)

            if system != "windows":
                os.chmod(self.ytdlp_path, 0o755)

            yield SetupProgress(
                file="yt-dlp",
                download_file_progress=DownloadFileProgress(
                    status=ProgressStatus.COMPLETED,
                    downloaded_bytes=0,
                    total_bytes=0,
                    percentage=100,
                ),
            )

    async def _setup_ffmpeg(self) -> AsyncGenerator[SetupProgress, Any]:
        """
        Download ffmpeg binary.

        :return: Async generator yielding SetupProgress objects.
        :rtype: AsyncGenerator[SetupProgress, Any]
        """
        system = platform.system().lower()
        self.ffmpeg_path = self.bin_dir / "ffmpeg.exe"
        self.ffprobe_path = self.bin_dir / "ffprobe.exe"

        if not self.ffmpeg_path.exists() or not self.ffprobe_path.exists():
            logger.info(f"Downloading ffmpeg for {system.capitalize()}...")
            
            # os = "win64" if system == "windows" else "linux64"
            # FORMAT = ""
            url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-n7.1-latest-win64-gpl-7.1.zip"
            temp_file = self.bin_dir / "ffmpeg.zip"

            async for progress in self._download_file(url, temp_file):
                yield SetupProgress(file="ffmpeg", download_file_progress=progress)
            progress.status = ProgressStatus.EXTRACTING
            yield SetupProgress(file="ffmpeg", download_file_progress=progress)
            await self._extract_ffmpeg_windows(temp_file)
            temp_file.unlink()

    async def _extract_ffmpeg_windows(self, zip_path: Path) -> None:
        """
        Extract only missing ffmpeg-related binaries from the Windows zip file.

        :param zip_path: Path to the ffmpeg zip file.
        :type zip_path: Path
        :return: None
        """

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            for file_info in zip_ref.infolist():
                filename = os.path.basename(file_info.filename)
                if filename not in ["ffmpeg.exe", "ffprobe.exe"]:
                    continue

                target_file = self.bin_dir / filename
                if target_file.exists():
                    continue 

                with zip_ref.open(file_info) as source, open(target_file, "wb") as target:
                    shutil.copyfileobj(source, target)

    async def _download_file(
        self, url: str, filepath: Path, max_retries: int = 5
    ) -> AsyncGenerator[DownloadFileProgress, Any]:
        """
        Download a file asynchronously with retries, timeout, resume support, and file size verification.

        :param url: URL to download from.
        :type url: str
        :param filepath: Path to save the file.
        :type filepath: Path
        :param max_retries: Maximum number of retries.
        :type max_retries: int
        :return: Async generator yielding DownloadFileProgress objects.
        :rtype: AsyncGenerator[DownloadFileProgress, Any]
        :raises AsyncYTBase: If download fails after max_retries.
        """
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
                                        status=ProgressStatus.DOWNLOADING,
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
        """
        Perform a health check on the required binaries (yt-dlp and ffmpeg).

        :return: HealthResponse object with health status and binary availability.
        :rtype: HealthResponse
        :raises Exception: If an unexpected error occurs during the health check process.
        """

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
                version=__version__,
            )

        except Exception as e:
            return HealthResponse(
                status="unhealthy",
                yt_dlp_available=False,
                ffmpeg_available=False,
                error=str(e),
                version=__version__,
            )

    def _get_format_selector(self, quality: "Quality") -> str:
        """Get yt-dlp format selector for quality. Use flexible format selection to let FFmpeg handle conversion."""
        if quality == Quality.BEST:
            return "bestvideo+bestaudio/best"
        elif quality == Quality.WORST:
            return "worst"
        elif quality == Quality.AUDIO_ONLY:
            return "bestaudio/best"
        elif quality == Quality.VIDEO_ONLY:
            return "bestvideo/best"
        else:
            height = quality.value.replace("p", "")
            return f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"

    def _build_download_command(self, url: str, config: "DownloadConfig") -> List[str]:
        """
        Build the yt-dlp command based on configuration.

        :param url: URL to download.
        :type url: str
        :param config: Download configuration.
        :type config: DownloadConfig
        :return: List of command arguments for yt-dlp.
        :rtype: List[str]
        """

        cmd = [str(self.ytdlp_path)]

        # Basic options
        cmd.extend(
            [
                "--no-warnings",
                "--progress",
                "--newline",
                "--no-playlist",
            ]
        )

        # Quality and format
        selected_quality = (
            Quality.AUDIO_ONLY if config.extract_audio else Quality(config.quality)
        )
        cmd.extend(["-f", self._get_format_selector(selected_quality)])

        if config.extract_audio:
            cmd.extend(["--extract-audio", "--audio-format", "mp3"])

        # Output template - use safe template that preserves Unicode
        if config.custom_filename:
            cmd.extend(["-o", config.custom_filename])
        else:
            # Use sanitized version but keep Unicode
            cmd.extend(["-o", "%(title).200B.%(ext)s"])

        # Thumbnail handling
        if config.embed_thumbnail or config.write_thumbnail:
            cmd.extend(["--write-thumbnail", "--convert-thumbnails", "jpg"])
        if config.embed_thumbnail:
            cmd.append("--embed-thumbnail")

        # Metadata and subtitles
        if config.write_subs:
            cmd.extend(["--write-subs", "--sub-lang", config.subtitle_lang])
        if config.embed_subs:
            cmd.append("--embed-subs")
        if config.embed_metadata:
            cmd.append("--add-metadata")
        if config.write_info_json:
            cmd.append("--write-info-json")
        if config.write_live_chat:
            cmd.append("--write-live-chat")

        # Network options
        if config.cookies_file:
            cmd.extend(["--cookies", str(Path(config.cookies_file).resolve())])
        if config.proxy:
            cmd.extend(["--proxy", config.proxy])
        if config.rate_limit:
            cmd.extend(["--limit-rate", config.rate_limit])

        # Retry options
        cmd.extend(
            [
                "--retries",
                str(config.retries),
                "--fragment-retries",
                str(config.fragment_retries),
            ]
        )

        # FFmpeg location
        if self.ffmpeg_path:
            cmd.extend(["--ffmpeg-location", str(self.ffmpeg_path)])

        # Progress template for parsing
        cmd.extend(
            [
                "--progress-template",
                "download:PROGRESS|%(progress._percent_str)s|%(progress._downloaded_bytes_str)s|%(progress._total_bytes_str)s|%(progress._speed_str)s|%(progress._eta_str)s",
            ]
        )
        cmd.append("--restrict-filenames")
        cmd.extend(["--print", "after_move:filepath"])

        # Output metadata as JSON for reliable parsing
        # cmd.append("--dump-single-json")

        # Custom options
        for key, value in config.custom_options.items():
            if isinstance(value, bool) and value:
                cmd.append(f"--{key}")
            elif not isinstance(value, bool):
                cmd.extend([f"--{key}", str(value)])

        cmd.append(url)

        return cmd

    async def _read_process_output(self, process):
        """
        Read process output line by line as UTF-8 (with replacement for bad chars).

        :param process: The process to read output from.
        :type process: asyncio.subprocess.Process
        :return: Async generator yielding lines of output.
        """
        assert process.stdout is not None, "Process must have stdout=PIPE"

        try:
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                data = line.decode("utf-8", errors="replace").rstrip()
                yield data

        except ValueError as e:
            if "chunk is longer than limit" in str(e):
                # yt-dlp --dump-single-json workaround
                data = await process.stdout.read()
                data = data.decode("utf-8", errors="replace").rstrip()
                yield data
            else:
                raise

    def _parse_progress(self, line: str, progress: DownloadProgress) -> None:
        """
        Parse progress information from yt-dlp output.

        :param line: Output line from yt-dlp.
        :type line: str
        :param progress: DownloadProgress object to update.
        :type progress: DownloadProgress
        :return: None
        """
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

    async def _parse_ffmpeg_progress(
        self, line: str, progress: DownloadProgress, callback, media_info: MediaInfo
    ) -> None:
        """
        Parse progress information from ffmpeg output.

        :param line: Output line from ffmpeg.
        :type line: str
        :param progress: DownloadProgress object to update.
        :type progress: DownloadProgress
        :param callback: Progress callback function.
        :param media_info: MediaInfo object for duration reference.
        :type media_info: MediaInfo
        :return: None
        """
        line = line.strip()
        if "progress=" in line:
            await call_callback(callback, progress)
        try:
            patterns = {
                "frame": re.compile(r"frame=(\d+)"),
                "fps": re.compile(r"fps=([\d\.]+)"),
                "bitrate": re.compile(r"bitrate=(\d+)"),
                "total_size": re.compile(r"total_size=(\d+)"),
                "out_time_us": re.compile(r"out_time_us=(\d+)"),
                "speed": re.compile(r"speed=([\d\.]+)"),
                "progress": re.compile(r"progress=(\d+)"),
            }
            for key_name, regex in patterns.items():
                key_matched = regex.search(line)
                if key_matched:
                    value = key_matched.group(1)
                    if key_name == "out_time_us":
                        value = int(value)
                        progress.ffmpeg_progress[key_name] = value
                        progress.percentage = round(
                            (value / 1_000_000) / media_info.duration * 100, 2
                        )
                        continue
                    if isinstance(progress.ffmpeg_progress[key_name], float):
                        progress.ffmpeg_progress[key_name] = float(value)
                    elif isinstance(progress.ffmpeg_progress[key_name], int):
                        progress.ffmpeg_progress[key_name] = int(value)
                    else:
                        progress.ffmpeg_progress[key_name] = str(value)
            return
        except (ValueError, IndexError) as e:
            pass

    def _parse_size(self, size_str: str) -> int:
        """
        Parse size string (e.g., '10.5MiB', '1.2GB') to bytes.

        :param size_str: Size string to parse.
        :type size_str: str
        :return: Size in bytes.
        :rtype: int
        """
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
        """
        Parse time string to seconds.

        :param time_str: Time string to parse.
        :type time_str: str
        :return: Time in seconds.
        :rtype: int
        """
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


class AsyncFFmpeg(BinaryManager):
    """
    AsyncFFmpeg: binary manager for media processing tasks.

    This class provides asynchronous methods to interact with FFmpeg and ffprobe binaries,
    enabling media file analysis, format conversion, codec compatibility checks, and progress reporting.
    It is designed to facilitate efficient and robust media processing workflows, including support for
    thumbnail embedding, output file management, and error handling.

    :param setup_only_ffmpeg: If True, only sets up FFmpeg binary. Defaults to True.
    :type setup_only_ffmpeg: bool
    :param bin_dir: Directory containing FFmpeg binaries. Defaults to None.
    :type bin_dir: Optional[str | Path]
    """

    def __init__(
        self, setup_only_ffmpeg: bool = True, bin_dir: Optional[str | Path] = None
    ):
        super().__init__(bin_dir)
        self._setup_only_ffmpeg = setup_only_ffmpeg

    async def get_file_info(self, file_path: str) -> MediaInfo:
        """
        Asynchronously retrieve media file information using ffprobe.

        :param file_path: Path to the media file to be analyzed.
        :type file_path: str
        :return: MediaInfo object containing metadata about the media file.
        :rtype: MediaInfo
        :raises FFmpegProcessingError: If ffprobe fails to process the file or returns a non-zero exit code.
        """

        cmd = [
            str(self.ffprobe_path),
            "-v",
            "error",
            "-show_entries",
            "format=filename,format_name,format_long_name,duration,size,bit_rate:stream=index,codec_name,codec_type,width,height,bit_rate,sample_rate,channels:stream_tags=language",
            "-of",
            "json",
            file_path,
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise FFmpegProcessingError(
                input_file=file_path,
                error_code=process.returncode,
                cmd=cmd,
                output=stderr.decode(),
            )

        data: dict = loads(stdout.decode())

        # Parse streams
        streams = []
        for s in data.get("streams", []):
            streams.append(
                StreamInfo(
                    index=s.get("index"),
                    codec_name=s.get("codec_name"),
                    codec_type=s.get("codec_type"),
                    width=s.get("width"),
                    height=s.get("height"),
                    bit_rate=int(s["bit_rate"]) if s.get("bit_rate") else None,
                    sample_rate=int(s["sample_rate"]) if s.get("sample_rate") else None,
                    channels=s.get("channels"),
                    language=(s.get("tags") or {}).get("language"),
                )
            )

        fmt = data.get("format", {})
        return MediaInfo(
            filename=fmt.get("filename", ""),
            format_name=fmt.get("format_name", ""),
            format_long_name=fmt.get("format_long_name", ""),
            duration=float(fmt["duration"]) if fmt.get("duration") else 0.0,
            size=int(fmt["size"]) if fmt.get("size") else 0,
            bit_rate=int(fmt["bit_rate"]) if fmt.get("bit_rate") else 0,
            streams=streams,
        )

    def _needs_process(
        self, ffmpeg_config: FFmpegConfig, media_info: MediaInfo
    ) -> bool:
        """
        Check if it needs processing or it's just already same as the config

        :param ffmpeg_config: the FFmpeg Config.
        :type ffmpeg_config: FFmpegConfig
        :param media_info: The Media info, You can get it by `get_file_info`.
        :type media_info: MediaInfo
        :return: Returns if it needs process or not.
        :rtype: bool
        """
        # Extract flags for readability
        fmt = (
            VideoFormat(ffmpeg_config.video_format)
            if ffmpeg_config.video_format
            else None
        )
        vcodec = VideoCodec(ffmpeg_config.video_codec)
        acodec = AudioCodec(ffmpeg_config.audio_codec)

        # --- 1. Check if output format mismatch ---
        if fmt:
            format_list = [f.strip().lower() for f in media_info.format_name.split(",")]
            if fmt.value.lower() not in format_list:
                logger.debug("Format mismatch")
                logger.debug(media_info.format_name.lower())
                logger.debug(fmt.value.lower())
                return True

        # --- 2. Handle removal/extraction cases ---
        if (
            ffmpeg_config.extract_audio
            or ffmpeg_config.remove_video
            or ffmpeg_config.remove_audio
        ):
            logger.debug("Stream removal/extraction requested")
            return True

        # --- 3. Check codecs ---
        for stream in media_info.streams:
            if stream.codec_type == "video":
                if vcodec != VideoCodec.COPY and stream.codec_name != vcodec.value:
                    logger.debug(
                        f"Video codec mismatch ({stream.codec_name} != {vcodec.value})"
                    )
                    return True
            elif stream.codec_type == "audio":
                if acodec != AudioCodec.COPY and stream.codec_name != acodec.value:
                    logger.debug(
                        f"Audio codec mismatch ({stream.codec_name} != {acodec.value})"
                    )
                    return True

        # --- 4. Resolution, FPS, bitrate, etc. ---
        if any(
            [
                ffmpeg_config.width,
                ffmpeg_config.height,
                ffmpeg_config.scale_filter,
                ffmpeg_config.fps,
                ffmpeg_config.video_bitrate,
                ffmpeg_config.audio_bitrate,
                ffmpeg_config.audio_sample_rate,
                ffmpeg_config.audio_channels,
            ]
        ):
            logger.debug("Custom output parameters specified")
            return True

        # --- 5. Filters ---
        if ffmpeg_config.video_filters or ffmpeg_config.audio_filters:
            logger.debug("Filters applied")
            return True

        return False

    async def process(
        self,
        file: str,
        ffmpeg_config: FFmpegConfig,
        progress_callback: Optional[
            Callable[[DownloadProgress], Union[None, Awaitable[None]]]
        ] = None,
        skip_checks: bool = False,
        id: Optional[str] = None,
        progress: Optional[DownloadProgress] = None,
        embed_thumbnail: bool = False,
        keep_thumbnail: bool = False,
    ) -> str:
        """
        Asynchronously process a media file using FFmpeg, handling format conversion, codec compatibility, and progress reporting.

        :param file: Path to the input media file.
        :type file: str
        :param ffmpeg_config: Configuration object for FFmpeg processing.
        :type ffmpeg_config: FFmpegConfig
        :param progress_callback: Callback function to report progress updates.
        :type progress_callback: Optional[Callable[[DownloadProgress], Union[None, Awaitable[None]]]]
        :param skip_checks: Skips checks for the processing file.
        :type skip_checks: bool
        :param id: the ID of the process.
        :type id: str
        :param progress: Initial progress state, if available.
        :type progress: Optional[DownloadProgress]
        :param embed_thumbnail: Whether to embed the thumbnail in the output.
        :type embed_thumbnail: bool
        :param keep_thumbnail: Whether to keep the thumbnail file after processing (for write_thumbnail mode).
        :type keep_thumbnail: bool
        :return: Filename of the processed output file.
        :rtype: str
        :raises CodecCompatibilityError: If the desired codec and format are incompatible and error raising is enabled.
        :raises FFmpegOutputExistsError: If the output file already exists and overwriting is disabled.
        :raises FFmpegProcessingError: If FFmpeg returns a non-zero exit code during processing.
        """

        media_info = await self.get_file_info(file)

        if not progress:
            progress = DownloadProgress(url="", percentage=0, id="")

        ffmpeg_config.add_media_input(file)

        if not skip_checks and not self._needs_process(ffmpeg_config, media_info):
            return file

        if embed_thumbnail and not any(inp.type == InputType.THUMBNAIL for inp in ffmpeg_config.inputs):
            file_path = Path(file)
            # Check for common thumbnail extensions that yt-dlp creates
            for thumb_ext in [".jpg", ".jpeg", ".webp", ".png"]:
                thumb_file = file_path.with_stem(file_path.stem).with_suffix(thumb_ext)
                if thumb_file.exists():
                    ffmpeg_config.add_thumbnail_input(str(thumb_file))
                    break
        
        

        if progress_callback:
            progress.status = ProgressStatus.ENCODING
            progress.percentage = 0
        ffmpeg_cmd = ffmpeg_config.build_command()
        output_file_path = Path(
            ffmpeg_config.output_path
        ) / ffmpeg_config.get_output_filename(Path(file).suffix.lstrip("."))
        if not ffmpeg_config.overwrite and output_file_path.exists():
            raise FFmpegOutputExistsError(str(output_file_path.absolute()))

        ffmpeg_process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=ffmpeg_config.output_path,
        )

        if id:
            self._downloads[id] = ffmpeg_process

        ffmpeg_output: List[str] = []

        async for line in self._read_process_output(ffmpeg_process):
            line = line.strip()
            ffmpeg_output.append(line)

            if line and progress_callback:
                await self._parse_ffmpeg_progress(
                    line, progress, progress_callback, media_info
                )

        ffmpeg_returncode = await ffmpeg_process.wait()

        if ffmpeg_returncode != 0:
            raise FFmpegProcessingError(
                input_file=file,
                output=ffmpeg_output[-20:],
                cmd=ffmpeg_cmd,
                error_code=ffmpeg_returncode,
            )

        if progress_callback:
            progress.status = ProgressStatus.COMPLETED
            progress.percentage = 100.0
            await call_callback(progress_callback, progress)

        if not keep_thumbnail:
            for inp in ffmpeg_config.inputs:
                if inp.type == InputType.THUMBNAIL and Path(inp.path).exists():
                    await delete_file(inp.path)

        if ffmpeg_config.delete_source and Path(file).exists():
            await delete_file(file)

        return ffmpeg_config.get_output_filename()
