from enum import Enum

__all__ = ["AudioFormat", "VideoFormat", "Quality"]


class AudioFormat(Enum):
    MP3 = "mp3"
    M4A = "m4a"
    WAV = "wav"
    FLAC = "flac"
    OGG = "ogg"


class VideoFormat(Enum):
    MP4 = "mp4"
    WEBM = "webm"
    MKV = "mkv"
    AVI = "avi"


class Quality(Enum):
    BEST = "best"
    WORST = "worst"
    AUDIO_ONLY = "bestaudio"
    VIDEO_ONLY = "bestvideo"
    HD_720P = "720p"
    HD_1080P = "1080p"
    HD_1440P = "1440p"
    UHD_4K = "2160p"
