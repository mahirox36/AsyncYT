import asyncio
import inspect
import os
from pathlib import Path
import hashlib
from typing import Dict, List, TYPE_CHECKING

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
]


async def call_callback(callback, *args, **kwargs):
    if inspect.iscoroutinefunction(callback):
        await callback(*args, **kwargs)
    else:
        callback(*args, **kwargs)


def get_unique_filename(file: Path, title: str) -> Path:
    base = file.with_name(title).with_suffix(file.suffix)
    new_file = base
    counter = 1

    while new_file.exists():
        new_file = file.with_name(f"{title} ({counter}){file.suffix}")
        counter += 1

    return new_file


def get_id(url: str, config: "DownloadConfig"):
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
    return codec in codec_compatibility.get(format, [])


def suggest_compatible_formats(video_codec: VideoCodec) -> List[VideoFormat]:
    return [fmt for fmt, codecs in codec_compatibility.items() if video_codec in codecs]


def is_audio_compatible(format: VideoFormat, codec: AudioCodec) -> bool:
    return codec in audio_codec_compatibility.get(format, [])


def suggest_audio_compatible_formats(audio_codec: AudioCodec) -> List[VideoFormat]:
    return [
        fmt
        for fmt, codecs in audio_codec_compatibility.items()
        if audio_codec in codecs
    ]


async def delete_file(path: str):
    await asyncio.to_thread(os.remove, path)
