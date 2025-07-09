from enum import StrEnum

__all__ = ["AudioFormat", "VideoFormat", "Quality"]


class AudioFormat(StrEnum):
    BEST = "best"
    MP3 = "mp3"
    M4A = "m4a"
    WAV = "wav"
    FLAC = "flac"
    OGG = "ogg"
    opus = "opus"
    aac = "aac"


class VideoFormat(StrEnum):
    MP4 = "mp4"
    WEBM = "webm"
    MKV = "mkv"
    AVI = "avi"
    FLV = "flv"
    MOV = "mov"


class Quality(StrEnum):
    BEST = "best"
    WORST = "worst"
    AUDIO_ONLY = "bestaudio"
    VIDEO_ONLY = "bestvideo"
    LOW_144P = "144p"
    LOW_240P = "240p"
    SD_480P = "480p"
    HD_720P = "720p"
    HD_1080P = "1080p"
    HD_1440P = "1440p"
    UHD_4K = "2160p"
    UHD_8K = "4320p"
