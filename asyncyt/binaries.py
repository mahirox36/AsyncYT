"""
AsyncYT - A comprehensive async Any website downloader library
Uses yt-dlp and ffmpeg with automatic binary management
"""

import asyncio
import logging
import os
import platform
import shutil
import tarfile
import zipfile
from asyncio.subprocess import Process
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Optional

import aiofiles
import aiohttp

from asyncyt.basemodels import (
    DownloadFileProgress,
    HealthResponse,
    SetupProgress,
)
from asyncyt.enums import ProgressStatus

from ._version import __version__
from .exceptions import AsyncYTBase

logger = logging.getLogger(__name__)

__all__ = ["BinaryManager"]


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

        if system == "windows":
            self.ytdlp_path = self.bin_dir / "yt-dlp.exe"
            self.ffmpeg_path = self.bin_dir / "ffmpeg.exe"
            self.ffprobe_path = self.bin_dir / "ffprobe.exe"
            self.node_path = self.bin_dir / "node.exe"
        elif system == "darwin":
            self.ytdlp_path = self.bin_dir / "yt-dlp_macos"
            self.ffmpeg_path = Path("ffmpeg")  # installed via brew
            self.ffprobe_path = Path("ffprobe")
            self.node_path = self.bin_dir / "node"
        else:  # linux
            self.ytdlp_path = self.bin_dir / "yt-dlp"
            self.ffmpeg_path = self.bin_dir / "ffmpeg"
            self.ffprobe_path = self.bin_dir / "ffprobe"
            self.node_path = self.bin_dir / "node"

        self._downloads: Dict[str, Process] = {}
        self._node_version_cache: Optional[str] = None

    async def setup_binaries_generator(self) -> AsyncGenerator[SetupProgress, Any]:
        """Download and setup all binaries, yielding SetupProgress."""
        self.bin_dir.mkdir(exist_ok=True)
        async for progress in self._setup_ytdlp():
            yield progress
        async for progress in self._setup_ffmpeg():
            yield progress
        async for progress in self._setup_node():
            yield progress
        logger.info("All binaries are ready!")

    async def setup_binaries(self) -> None:
        """Download and setup all binaries (fire-and-forget)."""
        async for _ in self.setup_binaries_generator():
            pass

    async def _setup_ytdlp(self) -> AsyncGenerator[SetupProgress, Any]:
        system = platform.system().lower()

        if system == "windows":
            url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
        elif system == "darwin":
            url = (
                "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos"
            )
        else:
            url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"

        def _completed() -> SetupProgress:
            return SetupProgress(
                file="yt-dlp",
                download_file_progress=DownloadFileProgress(
                    status=ProgressStatus.COMPLETED,
                    downloaded_bytes=0,
                    total_bytes=0,
                    percentage=100,
                ),
            )

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
                    "-U",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                _, stderr = await process.communicate()
                if process.returncode != 0:
                    logger.warning("yt-dlp update failed: %s", stderr.decode().strip())
            except Exception as exc:
                logger.warning("yt-dlp update error: %s", exc)
            yield _completed()
        else:
            logger.info("Downloading yt-dlp...")
            async for progress in self._download_file(url, self.ytdlp_path):
                yield SetupProgress(file="yt-dlp", download_file_progress=progress)
            if system != "windows":
                os.chmod(self.ytdlp_path, 0o755)
            yield _completed()

    async def _setup_ffmpeg(self) -> AsyncGenerator[SetupProgress, Any]:
        system = platform.system().lower()

        def _progress(status: ProgressStatus, pct: float = 0) -> SetupProgress:
            return SetupProgress(
                file="ffmpeg",
                download_file_progress=DownloadFileProgress(
                    status=status,
                    downloaded_bytes=0,
                    total_bytes=0,
                    percentage=pct,
                ),
            )

        if system == "darwin":
            yield _progress(ProgressStatus.DOWNLOADING)
            if shutil.which("brew") is None:
                raise AsyncYTBase(
                    "Homebrew is not installed. Install it from https://brew.sh"
                )
            process = await asyncio.create_subprocess_exec(
                "brew",
                "install",
                "ffmpeg",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await process.communicate()
            if process.returncode != 0:
                raise AsyncYTBase(
                    f"brew install ffmpeg failed: {stderr.decode().strip()}"
                )
            yield _progress(ProgressStatus.COMPLETED, 100)
            return

        if self.ffmpeg_path.exists() and self.ffprobe_path.exists():
            return

        logger.info("Downloading ffmpeg for %s...", system.capitalize())

        if system == "windows":
            arch_tag = "win64"
            url = (
                f"https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
                f"ffmpeg-n7.1-latest-{arch_tag}-gpl-7.1.zip"
            )
            temp_file = self.bin_dir / "ffmpeg.zip"
        else:  # linux
            arch_tag = "linux64"
            url = (
                f"https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
                f"ffmpeg-n7.1-latest-{arch_tag}-gpl-7.1.tar.xz"
            )
            temp_file = self.bin_dir / "ffmpeg.tar.xz"

        async for progress in self._download_file(url, temp_file):
            yield SetupProgress(file="ffmpeg", download_file_progress=progress)

        last_progress = DownloadFileProgress(
            status=ProgressStatus.EXTRACTING,
            downloaded_bytes=0,
            total_bytes=0,
            percentage=100,
        )
        yield SetupProgress(file="ffmpeg", download_file_progress=last_progress)

        if system == "windows":
            await self._extract_ffmpeg_zip(temp_file)
        else:
            await self._extract_ffmpeg_tar(temp_file)

        temp_file.unlink(missing_ok=True)
        yield _progress(ProgressStatus.COMPLETED, 100)

    async def _extract_ffmpeg_zip(self, zip_path: Path) -> None:
        """Extract ffmpeg/ffprobe from a zip (Windows)."""
        targets = {"ffmpeg.exe", "ffprobe.exe"}
        with zipfile.ZipFile(zip_path, "r") as zf:
            for info in zf.infolist():
                name = os.path.basename(info.filename)
                if name not in targets:
                    continue
                dest = self.bin_dir / name
                if dest.exists():
                    continue
                with zf.open(info) as src, open(dest, "wb") as dst:
                    shutil.copyfileobj(src, dst)

    async def _extract_ffmpeg_tar(self, tar_path: Path) -> None:
        """Extract ffmpeg/ffprobe from a tar.xz (Linux)."""
        targets = {"ffmpeg", "ffprobe"}
        with tarfile.open(tar_path, "r:xz") as tf:
            for member in tf.getmembers():
                name = os.path.basename(member.name)
                if name not in targets:
                    continue
                dest = self.bin_dir / name
                if dest.exists():
                    continue
                f = tf.extractfile(member)
                if f:
                    with open(dest, "wb") as dst:
                        shutil.copyfileobj(f, dst)
                    os.chmod(dest, 0o755)

    async def _setup_node(self) -> AsyncGenerator[SetupProgress, Any]:
        """Download and extract portable Node.js for JS runtime support."""
        if self.node_path.exists():
            return

        system = platform.system().lower()
        version = "v22.22.2"
        machine = platform.machine().lower()
        arch = "arm64" if machine in ("arm64", "aarch64") else "x64"

        if system == "windows":
            url = f"https://nodejs.org/dist/{version}/node-{version}-win-{arch}.zip"
            ext = ".zip"
        elif system == "darwin":
            url = (
                f"https://nodejs.org/dist/{version}/node-{version}-darwin-{arch}.tar.gz"
            )
            ext = ".tar.gz"
        else:
            url = (
                f"https://nodejs.org/dist/{version}/node-{version}-linux-{arch}.tar.xz"
            )
            ext = ".tar.xz"

        temp_file = self.bin_dir / f"node_temp{ext}"

        async for progress in self._download_file(url, temp_file):
            yield SetupProgress(file="nodejs", download_file_progress=progress)

        yield SetupProgress(
            file="nodejs",
            download_file_progress=DownloadFileProgress(
                status=ProgressStatus.EXTRACTING,
                percentage=100,
            ),
        )

        try:
            if system == "windows":
                with zipfile.ZipFile(temp_file, "r") as zf:
                    for member in zf.namelist():
                        if member.endswith("node.exe"):
                            with (
                                zf.open(member) as src,
                                open(self.node_path, "wb") as dst,
                            ):
                                shutil.copyfileobj(src, dst)
                            break
            else:
                mode = "r:gz" if ext.endswith(".gz") else "r:xz"
                with tarfile.open(temp_file, mode) as tf:
                    for member in tf.getmembers():
                        if member.name.endswith("/bin/node"):
                            f = tf.extractfile(member)
                            if f:
                                with open(self.node_path, "wb") as dst:
                                    shutil.copyfileobj(f, dst)
                            break
                os.chmod(self.node_path, 0o755)
        finally:
            temp_file.unlink(missing_ok=True)

    async def health_check(self) -> HealthResponse:
        """Perform a health check on yt-dlp and ffmpeg."""

        async def _check(cmd: str, *args: str) -> bool:
            try:
                proc = await asyncio.create_subprocess_exec(
                    cmd,
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
                return proc.returncode == 0
            except Exception:
                return False

        try:
            ytdlp_ok = self.ytdlp_path.exists() and await _check(
                str(self.ytdlp_path), "--version"
            )
            ffmpeg_cmd = (
                str(self.ffmpeg_path)
                if self.ffmpeg_path != Path("ffmpeg")
                else "ffmpeg"
            )
            ffmpeg_ok = await _check(ffmpeg_cmd, "-version")
            status = "healthy" if (ytdlp_ok and ffmpeg_ok) else "degraded"
            return HealthResponse(
                status=status,
                yt_dlp_available=ytdlp_ok,
                ffmpeg_available=ffmpeg_ok,
                binaries_path=str(self.bin_dir),
                version=__version__,
            )
        except Exception as exc:
            return HealthResponse(
                status="unhealthy",
                yt_dlp_available=False,
                ffmpeg_available=False,
                error=str(exc),
                version=__version__,
            )

    async def _download_file(
        self, url: str, filepath: Path, max_retries: int = 5
    ) -> AsyncGenerator[DownloadFileProgress, Any]:
        temp_filepath = filepath.with_suffix(filepath.suffix + ".part")
        backoff = 2

        for attempt in range(1, max_retries + 1):
            try:
                resume_pos = (
                    temp_filepath.stat().st_size if temp_filepath.exists() else 0
                )
                headers = {"Range": f"bytes={resume_pos}-"} if resume_pos else {}

                timeout_obj = aiohttp.ClientTimeout(
                    total=None, sock_connect=30, sock_read=300
                )
                async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                    async with session.get(url, headers=headers) as response:
                        if response.status not in (200, 206):
                            raise AsyncYTBase(f"HTTP {response.status} for {url}")

                        mode = "ab" if resume_pos and response.status == 206 else "wb"
                        content_length = int(response.headers.get("Content-Length", 0))
                        total = (
                            content_length + resume_pos
                            if response.status == 206
                            else content_length
                        )
                        downloaded = resume_pos

                        async with aiofiles.open(temp_filepath, mode) as f:
                            async for chunk in response.content.iter_chunked(65536):
                                await f.write(chunk)
                                downloaded += len(chunk)
                                yield DownloadFileProgress(
                                    status=ProgressStatus.DOWNLOADING,
                                    downloaded_bytes=downloaded,
                                    total_bytes=total,
                                    percentage=(downloaded / total * 100)
                                    if total
                                    else 0,
                                )

                        if total and temp_filepath.stat().st_size != total:
                            raise AsyncYTBase(
                                f"Incomplete download: expected {total}, got {temp_filepath.stat().st_size}"
                            )
                        temp_filepath.rename(filepath)
                        return

            except (asyncio.TimeoutError, AsyncYTBase, Exception) as exc:
                wait = min(backoff**attempt, 60)
                logger.warning(
                    "Download attempt %d/%d failed for %s: %s. Retrying in %ds…",
                    attempt,
                    max_retries,
                    url,
                    exc,
                    wait,
                )
                await asyncio.sleep(wait)

        raise AsyncYTBase(f"Failed to download {url} after {max_retries} attempts.")
