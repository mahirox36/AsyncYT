import asyncio
import inspect
import os
from pathlib import Path
import hashlib
from typing import Dict, List, TYPE_CHECKING
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from .enums import AudioCodec, VideoCodec, VideoFormat

if TYPE_CHECKING:
    from .basemodels import DownloadConfig

__all__ = [
    "call_callback",
    "get_unique_filename",
    "get_id",
    "codec_compatibility",
    "audio_codec_compatibility",
    "is_compatible",
    "suggest_compatible_formats",
    "is_audio_compatible",
    "suggest_audio_compatible_formats",
    "delete_file",
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


codec_compatibility: Dict[VideoFormat, List[VideoCodec]] = {
    VideoFormat.MP4: [
        VideoCodec.H264,
        VideoCodec.H265,
        VideoCodec.H264_NVENC,
        VideoCodec.HEVC_NVENC,
        VideoCodec.H264_QSV,
        VideoCodec.HEVC_QSV,
        VideoCodec.H264_AMF,
        VideoCodec.HEVC_AMF,
        VideoCodec.H264_VULKAN,
        VideoCodec.HEVC_VULKAN,
        VideoCodec.PRORES,
        VideoCodec.COPY,
    ],
    VideoFormat.WEBM: [
        VideoCodec.VP8,
        VideoCodec.VP9,
        VideoCodec.THEORA,
        VideoCodec.AV1,
        VideoCodec.AV1,
    ],
    VideoFormat.MKV: [
        VideoCodec.H264,
        VideoCodec.H265,
        VideoCodec.VP8,
        VideoCodec.VP9,
        VideoCodec.AV1,
        VideoCodec.PRORES,
        VideoCodec.DNXHD,
        VideoCodec.THEORA,
        VideoCodec.COPY,
    ],
    VideoFormat.MOV: [
        VideoCodec.H264,
        VideoCodec.H265,
        VideoCodec.PRORES,
        VideoCodec.DNXHD,
        VideoCodec.MJPEG,
        VideoCodec.COPY,
    ],
    VideoFormat.AVI: [
        VideoCodec.H264,
        VideoCodec.MJPEG,
        VideoCodec.DNXHD,
        VideoCodec.COPY,
    ],
}
audio_codec_compatibility: Dict[VideoFormat, List[AudioCodec]] = {
    VideoFormat.MP4: [
        AudioCodec.AAC,
        AudioCodec.MP3,
        AudioCodec.ALAC,
        AudioCodec.AC3,
        AudioCodec.EAC3,
        AudioCodec.DTS,
        AudioCodec.PCM_S16LE,
        AudioCodec.PCM_S24LE,
        AudioCodec.COPY,
    ],
    VideoFormat.WEBM: [
        AudioCodec.OPUS,
        AudioCodec.VORBIS,
        AudioCodec.FLAC,
        AudioCodec.COPY,
    ],
    VideoFormat.MKV: [
        AudioCodec.AAC,
        AudioCodec.MP3,
        AudioCodec.FLAC,
        AudioCodec.OPUS,
        AudioCodec.VORBIS,
        AudioCodec.ALAC,
        AudioCodec.AC3,
        AudioCodec.EAC3,
        AudioCodec.DTS,
        AudioCodec.PCM_S16LE,
        AudioCodec.PCM_S24LE,
        AudioCodec.AMR_NB,
        AudioCodec.AMR_WB,
        AudioCodec.WAVPACK,
        AudioCodec.COPY,
    ],
    VideoFormat.MOV: [
        AudioCodec.AAC,
        AudioCodec.ALAC,
        AudioCodec.PCM_S16LE,
        AudioCodec.PCM_S24LE,
        AudioCodec.COPY,
    ],
    VideoFormat.AVI: [
        AudioCodec.MP3,
        AudioCodec.PCM_S16LE,
        AudioCodec.PCM_S24LE,
        AudioCodec.COPY,
    ],
}


def is_compatible(format: VideoFormat, codec: VideoCodec) -> bool:
    """
    Check if a video codec is compatible with a container format.

    :param format: Video container format.
    :type format: VideoFormat
    :param codec: Video codec.
    :type codec: VideoCodec
    :return: True if compatible, False otherwise.
    :rtype: bool
    """
    return codec in codec_compatibility.get(format, [])


def suggest_compatible_formats(video_codec: VideoCodec) -> List[VideoFormat]:
    """
    Suggest compatible container formats for a given video codec.

    :param video_codec: Video codec.
    :type video_codec: VideoCodec
    :return: List of compatible formats.
    :rtype: List[VideoFormat]
    """
    return [fmt for fmt, codecs in codec_compatibility.items() if video_codec in codecs]


def is_audio_compatible(format: VideoFormat, codec: AudioCodec) -> bool:
    """
    Check if an audio codec is compatible with a container format.

    :param format: Video container format.
    :type format: VideoFormat
    :param codec: Audio codec.
    :type codec: AudioCodec
    :return: True if compatible, False otherwise.
    :rtype: bool
    """
    return codec in audio_codec_compatibility.get(format, [])


def suggest_audio_compatible_formats(audio_codec: AudioCodec) -> List[VideoFormat]:
    """
    Suggest compatible container formats for a given audio codec.

    :param audio_codec: Audio codec.
    :type audio_codec: AudioCodec
    :return: List of compatible formats.
    :rtype: List[VideoFormat]
    """
    return [
        fmt
        for fmt, codecs in audio_codec_compatibility.items()
        if audio_codec in codecs
    ]


async def delete_file(path: str):
    """
    Asynchronously delete a file.

    :param path: Path to the file to delete.
    :type path: str
    """
    await asyncio.to_thread(os.remove, path)


def get_unique_path(dir: Path, name: str) -> Path:
    """
    Get Unique Path if path exists

    :param dir: The dir of the file
    :type dir: Path
    :param name: the Original File name
    :type name: str
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
