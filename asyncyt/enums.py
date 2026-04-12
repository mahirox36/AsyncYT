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
    "TuneOption",
    "PixelFormat",
    "AudioChannels",
    "SubtitleFormat",
    "PlaylistStatus",
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
    ALAC = "alac"
    AIFF = "aiff"
    MKA = "mka"
    VORBIS = "vorbis"


class VideoFormat(StrEnum):
    MP4 = "mp4"
    WEBM = "webm"
    MKV = "mkv"
    AVI = "avi"
    FLV = "flv"
    MOV = "mov"
    GIF = "gif"


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
    AV1_SVT = "libsvtav1"
    AV1_RAV1E = "librav1e"

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

    # Hardware accelerated (Apple VideoToolbox)
    H264_VIDEOTOOLBOX = "h264_videotoolbox"
    HEVC_VIDEOTOOLBOX = "hevc_videotoolbox"

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
    PCM_S32LE = "pcm_s32le"
    PCM_F32LE = "pcm_f32le"
    AMR_NB = "libopencore_amrnb"
    AMR_WB = "libopencore_amrwb"
    WAVPACK = "wavpack"
    COPY = "copy"


class Preset(StrEnum):
    """Encoding presets for speed vs quality (x264/x265/NVENC)"""

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


class TuneOption(StrEnum):
    """x264/x265 tune options"""

    FILM = "film"
    ANIMATION = "animation"
    GRAIN = "grain"
    STILLIMAGE = "stillimage"
    FASTDECODE = "fastdecode"
    ZEROLATENCY = "zerolatency"
    PSNR = "psnr"
    SSIM = "ssim"


class PixelFormat(StrEnum):
    """Pixel format options for FFmpeg output"""

    YUV420P = "yuv420p"
    YUV422P = "yuv422p"
    YUV444P = "yuv444p"
    YUV420P10LE = "yuv420p10le"
    YUV422P10LE = "yuv422p10le"
    YUV444P10LE = "yuv444p10le"
    YUV420P12LE = "yuv420p12le"
    RGB24 = "rgb24"
    RGBA = "rgba"
    GBRP = "gbrp"
    GBRP10LE = "gbrp10le"


class AudioChannels(StrEnum):
    """Common audio channel layout presets"""

    MONO = "1"
    STEREO = "2"
    SURROUND_5_1 = "6"
    SURROUND_7_1 = "8"


class SubtitleFormat(StrEnum):
    """Subtitle conversion formats supported by yt-dlp"""

    SRT = "srt"
    VTT = "vtt"
    ASS = "ass"
    LRC = "lrc"


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
    UPDATING = "updating"
    EXTRACTING = "extracting"
    REMUXING = "remuxing"
    MERGING = "merging"


class PlaylistStatus(StrEnum):
    """Status of a playlist download operation"""

    PENDING = "pending"
    FETCHING_INFO = "fetching_info"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"
