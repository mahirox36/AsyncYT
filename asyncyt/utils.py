import inspect
from pathlib import Path
import hashlib
from typing import TYPE_CHECKING
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

if TYPE_CHECKING:
    from .basemodels import DownloadConfig

__all__ = [
    "call_callback",
    "get_unique_filename",
    "get_id",
    "get_unique_path",
    "clean_youtube_url",
]


async def call_callback(callback, *args, **kwargs):
    """
    Call a callback, supporting both coroutine and regular functions.

    :param callback: The callback function to call.
    :param args: Positional arguments for the callback.
    :param kwargs: Keyword arguments for the callback.
    """
    if inspect.iscoroutinefunction(callback):
        await callback(*args, **kwargs)
    else:
        callback(*args, **kwargs)


def get_unique_filename(file: Path, title: str) -> Path:
    """
    Generate a unique filename in the same directory, avoiding overwrites.

    :param file: Original file path.
    :type file: Path
    :param title: Desired title for the file.
    :type title: str
    :return: Unique file path.
    :rtype: Path
    """
    base = file.with_name(title).with_suffix(file.suffix)
    new_file = base
    counter = 1

    while new_file.exists():
        new_file = file.with_name(f"{title} ({counter}){file.suffix}")
        counter += 1

    return new_file


def get_id(url: str, config: "DownloadConfig"):
    """
    Generate a unique ID for a download based on URL and config.

    :param url: Download URL.
    :type url: str
    :param config: Download configuration.
    :type config: DownloadConfig
    :return: SHA256 hash string.
    :rtype: str
    """
    combined = url + config.model_dump_json()
    return hashlib.sha256(combined.encode()).hexdigest()


def get_unique_path(dir: Path, name: str) -> Path:
    """
    Get Unique Path if path exists

    :param dir: The dir of the file
    :type dir: Path
    :param name: the Original File name
    :type name: str
    :return: The Unique Path for that dir, for example `Videos/Unique Video (2).mp4`
    :rtype: Path
    """
    base = dir / name
    if not base.exists():
        return base

    stem = base.stem
    suffix = base.suffix
    counter = 2

    while True:
        new_name = f"{stem} ({counter}){suffix}"
        candidate = dir / new_name
        if not candidate.exists():
            return candidate
        counter += 1


def clean_youtube_url(url: str) -> str:
    """
    Clean any YouTube URL (watch, youtu.be, shorts, embed) into its core form.

    :param url: The youtube URL
    :type url: str
    :return: Cleaned YouTube URL.
    """
    parsed = urlparse(url)

    # short link URL
    if parsed.netloc in ["youtu.be"]:
        video_id = parsed.path.lstrip("/")
        qs = parse_qs(parsed.query)
        params = {"v": video_id}
        return f"https://www.youtube.com/watch?{urlencode(params)}"

    # shorts URL
    if "youtube.com" in parsed.netloc and parsed.path.startswith("/shorts/"):
        video_id = parsed.path.split("/")[2]
        qs = parse_qs(parsed.query)
        params = {"v": video_id}
        return f"https://www.youtube.com/watch?{urlencode(params)}"

    # embed URL
    if "youtube.com" in parsed.netloc and parsed.path.startswith("/embed/"):
        video_id = parsed.path.split("/")[2]
        qs = parse_qs(parsed.query)
        params = {"v": video_id}
        return f"https://www.youtube.com/watch?{urlencode(params)}"

    # Standard URL
    if parsed.netloc in ["www.youtube.com", "youtube.com"] and parsed.path == "/watch":
        qs = parse_qs(parsed.query)
        params = {}
        if "v" in qs:
            params["v"] = qs["v"][0]
        parsed = parsed._replace(query=urlencode(params, doseq=True))
        return urlunparse(parsed)

    return url
