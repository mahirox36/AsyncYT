from enum import StrEnum

__all__ = [
    "AudioFormat",
    "VideoFormat",
    "Quality",
    "VideoCodec",
    "AudioCodec",
    "Preset",
    "InputType",
    "ProgressStatus",
]


class AudioFormat(StrEnum):
    COPY = "copy"
    MP3 = "mp3"
    M4A = "m4a"
    WAV = "wav"
    FLAC = "flac"
    OGG = "ogg"
    OPUS = "opus"
    AAC = "aac"
    AC3 = "ac3"
    EAC3 = "eac3"
    DTS = "dts"
    AMR = "amr"
    AWB = "awb"
    WV = "wv"


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


class VideoCodec(StrEnum):
    """Video codec options"""

    # Software codecs
    H264 = "libx264"
    H265 = "libx265"
    VP9 = "libvpx-vp9"
    VP8 = "libvpx"
    AV1 = "libaom-av1"

    # Hardware accelerated (NVIDIA)
    H264_NVENC = "h264_nvenc"
    HEVC_NVENC = "hevc_nvenc"
    AV1_NVENC = "av1_nvenc"

    # Hardware accelerated (Intel QSV)
    H264_QSV = "h264_qsv"
    HEVC_QSV = "hevc_qsv"
    AV1_QSV = "av1_qsv"

    # Hardware accelerated (AMD AMF)
    H264_AMF = "h264_amf"
    HEVC_AMF = "hevc_amf"

    # Vulkan
    H264_VULKAN = "h264_vulkan"
    HEVC_VULKAN = "hevc_vulkan"

    # Other
    MJPEG = "mjpeg"
    PRORES = "prores"
    DNXHD = "dnxhd"
    THEORA = "libtheora"
    H263 = "h263"
    H261 = "h261"
    CINEFORM = "cineform"
    COPY = "copy"


class AudioCodec(StrEnum):
    """Audio codec options"""

    AAC = "aac"
    MP3 = "libmp3lame"
    OPUS = "libopus"
    VORBIS = "libvorbis"
    FLAC = "flac"
    ALAC = "alac"
    AC3 = "ac3"
    EAC3 = "eac3"
    DTS = "dca"
    PCM_S16LE = "pcm_s16le"
    PCM_S24LE = "pcm_s24le"
    AMR_NB = "libopencore_amrnb"
    AMR_WB = "libopencore_amrwb"
    WAVPACK = "wavpack"
    COPY = "copy"


class Preset(StrEnum):
    """Encoding presets for speed vs quality"""

    ULTRAFAST = "ultrafast"
    SUPERFAST = "superfast"
    VERYFAST = "veryfast"
    FASTER = "faster"
    FAST = "fast"
    MEDIUM = "medium"
    SLOW = "slow"
    SLOWER = "slower"
    VERYSLOW = "veryslow"
    PLACEBO = "placebo"


class InputType(StrEnum):
    """Input file types"""

    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLE = "subtitle"
    THUMBNAIL = "thumbnail"
    IMAGE = "image"


class ProgressStatus(StrEnum):
    """Progress Status types"""

    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    ENCODING = "encoding"
    COMPLETED = "completed"
    EXTRACTING = "extracting"
