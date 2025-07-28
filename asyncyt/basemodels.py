import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


from .utils import (
    is_compatible,
    is_audio_compatible,
    suggest_audio_compatible_formats,
    suggest_compatible_formats,
)
from .exceptions import CodecCompatibilityError, InvalidFFmpegConfigError
from .enums import *

__all__ = [
    "VideoInfo",
    "DownloadConfig",
    "DownloadProgress",
    "DownloadRequest",
    "SearchRequest",
    "PlaylistRequest",
    "DownloadResponse",
    "SearchResponse",
    "PlaylistResponse",
    "HealthResponse",
    "DownloadFileProgress",
    "SetupProgress",
    "InputFile",
    "FFmpegConfig",
    "FFmpegProgress",
    "StreamInfo",
    "MediaInfo",
]


class VideoInfo(BaseModel):
    """Video information extracted from URL"""

    url: str
    title: str
    duration: float = Field(0, ge=-1)
    uploader: str
    view_count: int = Field(0, ge=-1)
    like_count: Optional[int] = Field(None, ge=-1)
    description: str = ""
    thumbnail: str = ""
    upload_date: str = ""
    formats: List[Dict[str, Any]] = Field(default_factory=list)

    @field_validator("url")
    def validate_url(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @classmethod
    def from_dict(cls, data: dict) -> "VideoInfo":
        return cls(
            url=data.get("webpage_url", ""),
            title=data.get("title", ""),
            duration=data.get("duration", 0),
            uploader=data.get("uploader", ""),
            view_count=data.get("view_count", 0),
            like_count=data.get("like_count"),
            description=data.get("description", ""),
            thumbnail=data.get("thumbnail", ""),
            upload_date=data.get("upload_date", ""),
            formats=data.get("formats", []),
        )

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "title": "Rick Astley - Never Gonna Give You Up",
                "duration": 212,
                "uploader": "RickAstleyVEVO",
                "view_count": 1000000000,
                "like_count": 10000000,
                "description": "Official video...",
                "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
                "upload_date": "20091025",
            }
        }


class InputFile(BaseModel):
    """Single input file configuration"""

    path: str = Field(description="Path to input file")
    type: InputType = Field(description="Type of input file")
    options: List[str] = Field(
        default_factory=list, description="Input-specific options"
    )
    stream_index: Optional[int] = Field(
        default=None, description="Specific stream index to use"
    )

    @field_validator("path")
    def validate_path_exists(cls, v):
        if not Path(v).exists():
            raise ValueError(f"Input file does not exist: {v}")
        return v


class FFmpegConfig(BaseModel):
    """Configuration for FFmpeg operations"""

    ffmpeg_path: str = Field(default="ffmpeg", description="Path of FFmpeg")
    # Input/Output
    inputs: List[InputFile] = Field(
        default_factory=list, description="List of input files"
    )
    output_path: str = Field(default="./output", description="Output directory path")
    output_filename: Optional[str] = Field(
        default=None, description="Output filename (without extension)"
    )

    # Video settings
    video_codec: VideoCodec = Field(default=VideoCodec.COPY, description="Video codec")
    video_format: Optional[VideoFormat] = Field(
        default=None, description="Output container format"
    )
    video_bitrate: Optional[str] = Field(
        default=None, description="Video bitrate (e.g., '2M', '1000k')"
    )
    crf: Optional[int] = Field(
        default=None,
        ge=0,
        le=51,
        description="Constant Rate Factor (0-51, lower = better quality)",
    )
    preset: Preset = Field(default=Preset.MEDIUM, description="Encoding preset")

    # Audio settings
    audio_codec: AudioCodec = Field(default=AudioCodec.COPY, description="Audio codec")
    audio_bitrate: Optional[str] = Field(
        default=None, description="Audio bitrate (e.g., '128k', '320k')"
    )
    audio_sample_rate: Optional[int] = Field(
        default=None, description="Audio sample rate in Hz"
    )
    audio_channels: Optional[int] = Field(
        default=None, ge=1, le=8, description="Number of audio channels"
    )

    # Resolution and scaling
    width: Optional[int] = Field(
        default=None, ge=1, description="Output width in pixels"
    )
    height: Optional[int] = Field(
        default=None, ge=1, description="Output height in pixels"
    )
    scale_filter: Optional[str] = Field(
        default=None, description="Custom scale filter (e.g., 'scale=1920:1080')"
    )

    # Frame rate
    fps: Optional[float] = Field(default=None, gt=0, description="Output frame rate")

    # Processing options
    extract_audio: bool = Field(default=False, description="Extract audio only")
    remove_video: bool = Field(default=False, description="Remove video stream")
    remove_audio: bool = Field(default=False, description="Remove audio stream")

    # Time ranges
    start_time: Optional[str] = Field(
        default=None, description="Start time (e.g., '00:01:30' or '90')"
    )
    duration: Optional[str] = Field(
        default=None, description="Duration (e.g., '00:02:00' or '120')"
    )
    end_time: Optional[str] = Field(
        default=None, description="End time (e.g., '00:03:30' or '210')"
    )

    # Filters
    video_filters: List[str] = Field(
        default_factory=list, description="Video filters to apply"
    )
    audio_filters: List[str] = Field(
        default_factory=list, description="Audio filters to apply"
    )

    # Hardware acceleration
    hardware_accel: Optional[str] = Field(
        default=None,
        description="Hardware acceleration (e.g., 'cuda', 'vaapi', 'videotoolbox')",
    )

    # Advanced options
    two_pass: bool = Field(default=False, description="Use two-pass encoding")
    overwrite: bool = Field(
        default=False, description="Overwrite output file if exists"
    )
    threads: Optional[int] = Field(
        default=None, ge=1, description="Number of threads to use"
    )
    delete_source: bool = Field(
        default=True, description="Whether to delete the source file after processing"
    )

    # Metadata
    preserve_metadata: bool = Field(default=True, description="Preserve input metadata")
    copy_subs: bool = Field(default=False, description="Copy subs into the output")
    copy_attachments: bool = Field(
        default=False,
        description="Copy the attachments into the output (attachments like thumbnail, fonts, etc)",
    )
    preserve_metadata: bool = Field(default=True, description="Preserve input metadata")
    custom_metadata: Dict[str, str] = Field(
        default_factory=dict, description="Custom metadata to add"
    )

    # Logging and debugging
    log_level: str = Field(default="info", description="FFmpeg log level")
    verbose: bool = Field(default=False, description="Enable verbose output")
    no_codec_compatibility_error: bool = Field(
        default=True,
        description="Auto-pick a compatible format if the chosen codec isn't supported.",
    )

    # Custom options
    custom_input_options: List[str] = Field(
        default_factory=list, description="Custom input options"
    )
    custom_output_options: List[str] = Field(
        default_factory=list, description="Custom output options"
    )
    _original_audio_type: Optional[str] = None
    _thumbnail_indexed: Optional[int] = None

    def add_input(
        self,
        path: str,
        input_type: InputType,
        options: Optional[List[str]] = None,
        stream_index: Optional[int] = None,
    ):
        """Add an input file to the configuration"""
        input_file = InputFile(
            path=path, type=input_type, options=options or [], stream_index=stream_index
        )
        self.inputs.append(input_file)

    def add_media_input(self, path: str, options: Optional[List[str]] = None):
        """Convenience method to add Video/Audio input"""
        ext = os.path.splitext(os.path.basename(path))[1][1:]
        if ext in [f.value for f in VideoFormat]:
            self.add_input(path, InputType.VIDEO, options)
            if not self.video_format:
                self.video_format = VideoFormat(
                    os.path.splitext(os.path.basename(path))[1][1:]
                )
        else:
            self.add_input(path, InputType.AUDIO, options)
            self._original_audio_type = os.path.splitext(os.path.basename(path))[1][1:]

    def add_subtitle_input(self, path: str, options: Optional[List[str]] = None):
        """Convenience method to add subtitle input"""
        self.add_input(path, InputType.SUBTITLE, options)

    def add_thumbnail_input(self, path: str, options: Optional[List[str]] = None):
        """Convenience method to add thumbnail input"""
        self.add_input(path, InputType.THUMBNAIL, options)

    def index_thumbnail_input(self, index: int):
        self._thumbnail_indexed = index

    @property
    def is_empty(self):
        if not self.video_format and not self.audio_codec:
            raise InvalidFFmpegConfigError(
                "At least one of video_format or audio_codec must be set."
            )
        return not any(
            [
                None if self.video_codec == VideoCodec.COPY else True,
                self.video_format,
                self.video_bitrate,
                self.crf,
                None if self.preset == Preset.MEDIUM else True,
                None if self.audio_codec == AudioCodec.COPY else True,
                self.audio_bitrate,
                self.audio_sample_rate,
                self.audio_channels,
                self.width,
                self.height,
                self.scale_filter,
                self.fps,
                self.extract_audio,
                self.remove_video,
                self.remove_audio,
                self.start_time,
                self.duration,
                self.end_time,
                self.video_filters,
                self.audio_filters,
                self.hardware_accel,
                self.custom_input_options,
                self.custom_output_options,
            ]
        )

    def build_command(self) -> List[str]:
        """Build the FFmpeg command based on configuration with dynamic format/codec handling"""
        cmd = [self.ffmpeg_path]

        # Add global options
        if self.hardware_accel:
            cmd.extend(["-hwaccel", self.hardware_accel])
        if self.threads:
            cmd.extend(["-threads", str(self.threads)])
        cmd.extend(["-loglevel", self.log_level])
        if self.overwrite:
            cmd.append("-y")

        # Input handling with reversed order for proper stream mapping
        input_sources = list(reversed(self.inputs))
        for inp in input_sources:
            cmd.extend(inp.options)
            cmd.extend(["-i", inp.path])

        # Time range options - applied globally
        if self.start_time:
            cmd.extend(["-ss", self.start_time])
        if self.duration:
            cmd.extend(["-t", self.duration])
        elif self.end_time:
            cmd.extend(["-to", self.end_time])

        # Determine output format constraints
        is_audio_only = self.extract_audio or self.remove_video
        has_video = not (is_audio_only or self.remove_video)
        has_audio = not self.remove_audio

        # Format-specific codec compatibility handling
        if self.video_format:
            fmt = VideoFormat(self.video_format)
            # Codec compatibility checks for different container formats
            if not is_compatible(format=fmt, codec=self.video_codec):
                if not self.no_codec_compatibility_error:
                    raise CodecCompatibilityError(self.video_codec, fmt)
                else:
                    self.video_format = suggest_compatible_formats(self.video_codec)[0]
            if not is_audio_compatible(format=fmt, codec=self.audio_codec):
                if not self.no_codec_compatibility_error:
                    raise CodecCompatibilityError(self.audio_codec, fmt)
                else:
                    self.video_format = suggest_audio_compatible_formats(
                        self.audio_codec
                    )[0]

        # Video encoding settings
        if has_video and self.video_codec:
            if not any(c in cmd for c in ["-c:v:0", "-c:v"]):
                cmd.extend(["-c:v:0", VideoCodec(self.video_codec).value])
            if self.video_codec != VideoCodec.COPY:
                if self.crf is not None:
                    cmd.extend(["-crf", str(self.crf)])
                if self.video_bitrate:
                    cmd.extend(["-b:v", self.video_bitrate])
                if self.preset:
                    cmd.extend(["-preset", Preset(self.preset).value])

        # Audio encoding settings
        if has_audio and self.audio_codec:
            if not any(c in cmd for c in ["-c:a"]):
                cmd.extend(["-c:a", AudioCodec(self.audio_codec).value])
            if self.audio_codec != AudioCodec.COPY:
                if self.audio_bitrate:
                    cmd.extend(["-b:a", self.audio_bitrate])
                if self.audio_sample_rate:
                    cmd.extend(["-ar", str(self.audio_sample_rate)])
                if self.audio_channels:
                    cmd.extend(["-ac", str(self.audio_channels)])

        # Video filters
        video_filters = list(self.video_filters)
        if has_video:
            if self.width and self.height:
                video_filters.append(f"scale={self.width}:{self.height}")
            elif self.scale_filter:
                video_filters.append(self.scale_filter)
        if video_filters:
            cmd.extend(["-vf", ",".join(video_filters)])

        # Audio filters
        if has_audio and self.audio_filters:
            cmd.extend(["-af", ",".join(self.audio_filters)])

        # Frame rate
        if has_video and self.fps:
            cmd.extend(["-r", str(self.fps)])

        # Stream handling
        if self.remove_video or self.extract_audio:
            cmd.extend(["-vn"])
        if self.remove_audio:
            cmd.extend(["-an"])

        # Metadata and stream mapping
        if not self.preserve_metadata:
            cmd.extend(["-map_metadata", "-1"])

        # Stream mapping with intelligent handling
        video_stream_count = 0
        stream_mapping = []
        for idx, inp in enumerate(input_sources):
            if inp.type == InputType.VIDEO and has_video:
                stream_spec = (
                    f"{idx}:{inp.stream_index}"
                    if inp.stream_index is not None
                    else f"{idx}:v:0"
                )
                stream_mapping.extend(["-map", stream_spec])
                video_stream_count += 1
                if has_audio:
                    stream_mapping.extend(
                        ["-map", f"{idx}:a:0?"]
                    )  # Optional audio stream

            elif inp.type == InputType.AUDIO and has_audio:
                stream_spec = (
                    f"{idx}:{inp.stream_index}"
                    if inp.stream_index is not None
                    else f"{idx}:a:0"
                )
                stream_mapping.extend(["-map", stream_spec])

            elif inp.type == InputType.SUBTITLE and self.copy_subs:
                stream_spec = (
                    f"{idx}:{inp.stream_index}"
                    if inp.stream_index is not None
                    else f"{idx}:s:0"
                )
                stream_mapping.extend(["-map", stream_spec])
                if self.video_format == VideoFormat.MKV:
                    cmd.extend(["-c:s", "copy"])
                else:
                    cmd.extend(["-c:s", "mov_text"])

            elif inp.type == InputType.THUMBNAIL:
                stream_mapping.extend(["-map", f"{idx}:v:0"])
                cmd.extend(
                    [
                        f"-c:v:{str(video_stream_count)}",
                        "mjpeg",
                        "-disposition:v:" + str(video_stream_count),
                        "attached_pic",
                    ]
                )
                video_stream_count += 1

        # Add all valid stream mappings
        if stream_mapping:
            cmd.extend(stream_mapping)

        # Custom metadata
        for key, value in self.custom_metadata.items():
            cmd.extend(["-metadata", f"{key}={value}"])

        # Two-pass encoding setup
        if self.two_pass and self.video_codec != VideoCodec.COPY and has_video:
            cmd.extend(["-pass", "1", "-f", "null"])

        # Custom options
        cmd.extend(self.custom_input_options)
        cmd.extend(self.custom_output_options)

        # Output file
        output_file = Path(self.output_path) / self.get_output_filename()
        cmd.extend(["-progress", "pipe:1"])
        cmd.append(str(output_file))

        return cmd

    def build_two_pass_commands(self) -> tuple[List[str], List[str]]:
        """Build two separate commands for two-pass encoding"""
        if not self.two_pass:
            raise ValueError("Two-pass encoding not enabled")

        # First pass
        first_pass = self.build_command()
        # Replace output with null and add pass 1
        for i, arg in enumerate(first_pass):
            if arg == str(Path(self.output_path) / self.get_output_filename()):
                first_pass[i] = "/dev/null" if Path("/dev/null").exists() else "NUL"
                break

        # Add pass 1 before output
        output_idx = len(first_pass) - 1
        first_pass.insert(output_idx, "-pass")
        first_pass.insert(output_idx + 1, "1")
        first_pass.insert(output_idx + 2, "-f")
        first_pass.insert(output_idx + 3, "null")

        # Second pass
        second_pass = self.build_command()
        output_idx = len(second_pass) - 1
        second_pass.insert(output_idx, "-pass")
        second_pass.insert(output_idx + 1, "2")

        return first_pass, second_pass

    def get_command_string(self) -> str:
        """Get the command as a formatted string"""
        cmd = self.build_command()
        # Escape arguments with spaces
        escaped_cmd = []
        for arg in cmd:
            if " " in arg and not (arg.startswith('"') and arg.endswith('"')):
                escaped_cmd.append(f'"{arg}"')
            else:
                escaped_cmd.append(arg)
        return " ".join(escaped_cmd)

    def get_audio_format(self, original_ext: Optional[str] = None):
        original_ext = original_ext or self._original_audio_type or "audio"
        audio_extensions = {
            AudioCodec.MP3: "mp3",
            AudioCodec.AAC: "aac",
            AudioCodec.FLAC: "flac",
            AudioCodec.OPUS: "opus",
            AudioCodec.VORBIS: "ogg",
            AudioCodec.ALAC: "m4a",
            AudioCodec.AC3: "ac3",
            AudioCodec.EAC3: "eac3",
            AudioCodec.DTS: "dts",
            AudioCodec.PCM_S16LE: "wav",
            AudioCodec.PCM_S24LE: "wav",
            AudioCodec.AMR_NB: "amr",
            AudioCodec.AMR_WB: "awb",
            AudioCodec.WAVPACK: "wv",
            AudioCodec.COPY: original_ext,
        }
        return audio_extensions.get(self.audio_codec, original_ext)

    def get_audio_codec(self, format: Optional[AudioFormat] = None) -> AudioCodec:
        ext = format or AudioFormat.COPY

        audio_extensions = {
            "mp3": AudioCodec.MP3,
            "aac": AudioCodec.AAC,
            "flac": AudioCodec.FLAC,
            "opus": AudioCodec.OPUS,
            "ogg": AudioCodec.VORBIS,
            "m4a": AudioCodec.ALAC,
            "ac3": AudioCodec.AC3,
            "eac3": AudioCodec.EAC3,
            "dts": AudioCodec.DTS,
            "wav": AudioCodec.PCM_S16LE,
            "amr": AudioCodec.AMR_NB,
            "awb": AudioCodec.AMR_WB,
            "wv": AudioCodec.WAVPACK,
        }

        return audio_extensions.get(ext.value, AudioCodec.COPY)

    def get_output_filename(self, original_ext: Optional[str] = None) -> str:
        """Generate output filename with proper extension"""
        base_name = self.output_filename or "output"
        is_audio_mode = (self.extract_audio and not self.remove_video) or (
            self.audio_codec and not self.video_format
        )

        if is_audio_mode:
            extension = self.get_audio_format(original_ext)
        else:
            if not self.video_format:
                raise InvalidFFmpegConfigError(
                    "At least one of video_format or audio_codec must be set."
                )
            extension = VideoFormat(self.video_format).value

        return f"{base_name}.{extension}"

    @field_validator("output_path")
    def validate_output_path(cls, v):
        # Create directory if it doesn't exist
        Path(v).mkdir(parents=True, exist_ok=True)
        return v

    @field_validator("video_bitrate", "audio_bitrate")
    def validate_bitrate(cls, v):
        if v and not any(v.endswith(unit) for unit in ["k", "K", "m", "M", "g", "G"]):
            if not v.isdigit():
                raise ValueError("Bitrate must be a number or end with k/K/m/M/g/G")
        return v

    @field_validator("start_time", "duration", "end_time")
    def validate_time_format(cls, v):
        if v is None:
            return v
        # Accept either seconds (numeric) or HH:MM:SS format
        if v.isdigit() or v.replace(".", "").isdigit():
            return v
        # Validate HH:MM:SS format
        parts = v.split(":")
        if len(parts) not in [2, 3]:
            raise ValueError("Time format must be 'SS', 'MM:SS', or 'HH:MM:SS'")
        try:
            for part in parts:
                float(part)
        except ValueError:
            raise ValueError("Invalid time format")
        return v

    @field_validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = [
            "quiet",
            "panic",
            "fatal",
            "error",
            "warning",
            "info",
            "verbose",
            "debug",
            "trace",
        ]
        if v not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
        return v

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "inputs": [
                    {"path": "video.mp4", "type": "video"},
                    {"path": "audio.mp3", "type": "audio"},
                    {"path": "subtitles.srt", "type": "subtitle"},
                    {"path": "thumbnail.jpg", "type": "thumbnail"},
                ],
                "output_path": "./output",
                "video_codec": "libx264",
                "video_format": "mp4",
                "crf": 23,
                "preset": "medium",
                "audio_codec": "aac",
                "audio_bitrate": "128k",
                "width": 1920,
                "height": 1080,
                "overwrite": True,
                "preserve_metadata": True,
            }
        }


class FFmpegProgress(BaseModel):
    frame: int = 0
    fps: float = 0.0
    bitrate: str = "0kbits/s"
    total_size: int = 0
    out_time_us: int = 0
    speed: str = "0x"
    progress: str = "unknown"

    @property
    def out_time_seconds(self) -> float:
        return self.out_time_us / 1_000_000.0

    def __setitem__(self, key: str, value):
        if key in self.model_fields:
            setattr(self, key, value)
        else:
            raise KeyError(f"{key!r} is not a valid field of FFmpegProgress")

    def __getitem__(self, key: str):
        # Pydantic models store fields in __dict__, so we can do setattr
        if key in self.model_fields:
            getattr(self, key)
        else:
            raise KeyError(f"{key!r} is not a valid field of FFmpegProgress")


class DownloadConfig(BaseModel):
    """Configuration for downloads"""

    output_path: str = Field(default="./downloads", description="Output directory path")
    quality: Quality = Field(default=Quality.BEST, description="Video quality setting")
    audio_format: Optional[AudioFormat] = Field(
        default=None, description="Audio format for extraction"
    )
    video_format: Optional[VideoFormat] = Field(
        default=None, description="Video format for output"
    )
    extract_audio: bool = Field(default=False, description="Extract audio only")
    embed_subs: bool = Field(default=False, description="Embed subtitles in video")
    write_subs: bool = Field(default=False, description="Write subtitle files")
    subtitle_lang: str = Field(default="en", description="Subtitle language code")
    write_thumbnail: bool = Field(default=False, description="Download thumbnail")
    embed_thumbnail: bool = Field(default=False, description="Embed thumbnail")
    embed_metadata: bool = Field(default=True, description="Embed metadata")
    write_info_json: bool = Field(default=False, description="Write info JSON file")
    custom_filename: Optional[str] = Field(
        default=None, description="Custom filename template"
    )
    cookies_file: Optional[str] = Field(
        default=None, description="Path to cookies file"
    )
    proxy: Optional[str] = Field(default=None, description="Proxy URL")
    rate_limit: Optional[str] = Field(
        default=None, description="Rate limit (e.g., '1M')"
    )
    retries: int = Field(default=3, ge=0, le=10, description="Number of retries")
    fragment_retries: int = Field(
        default=3, ge=0, le=10, description="Fragment retries"
    )
    custom_options: Dict[str, Any] = Field(
        default_factory=dict, description="Custom yt-dlp options"
    )
    ffmpeg_config: FFmpegConfig = Field(
        default_factory=FFmpegConfig, description="Custom FFmpeg config"
    )

    @field_validator("output_path")
    def validate_output_path(cls, v):
        # Create directory if it doesn't exist
        Path(v).mkdir(parents=True, exist_ok=True)
        return v

    @field_validator("rate_limit")
    def validate_rate_limit(cls, v):
        if v and not any(v.endswith(unit) for unit in ["K", "M", "G", "k", "m", "g"]):
            if not v.isdigit():
                raise ValueError("Rate limit must be a number or end with K/M/G")
        return v

    @model_validator(mode="after")
    def handle_extract_audio(self):
        # If extract_audio is True, force embed_subs to False
        if self.extract_audio:
            self.embed_subs = False
        return self

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "output_path": "./downloads",
                "quality": "720p",
                "extract_audio": True,
                "audio_format": "mp3",
                "write_thumbnail": True,
                "embed_thumbnail": True,
                "subtitle_lang": "en",
                "retries": 3,
            }
        }


class DownloadProgress(BaseModel):
    """Progress information for downloads"""

    id: str
    url: str
    title: str = ""
    status: ProgressStatus = ProgressStatus.DOWNLOADING
    downloaded_bytes: int = 0
    total_bytes: int = 0
    speed: str = ""
    eta: int = 0
    percentage: float = Field(0.0, ge=0.0, le=100.0)
    ffmpeg_progress: FFmpegProgress = Field(default_factory=FFmpegProgress)

    @property
    def is_complete(self) -> bool:
        return self.status == ProgressStatus.COMPLETED

    class Config:
        json_encoders = {float: lambda v: round(v, 2)}


class DownloadFileProgress(BaseModel):
    """Progress information for File downloads"""

    status: ProgressStatus = ProgressStatus.DOWNLOADING
    downloaded_bytes: int = 0
    total_bytes: int = 0
    percentage: float = Field(0.0, ge=0.0, le=100.0)

    @property
    def is_complete(self) -> bool:
        return self.status == ProgressStatus.COMPLETED

    class Config:
        json_encoders = {float: lambda v: round(v, 2)}


class SetupProgress(BaseModel):
    """Progress information for File downloads"""

    file: str = "yt-dlp"
    download_file_progress: DownloadFileProgress = Field(
        description="the progress of the file being downloaded"
    )

    class Config:
        json_encoders = {float: lambda v: round(v, 2)}


# API Response Models
class DownloadRequest(BaseModel):
    """Request model for download endpoints"""

    url: str = Field(..., description="Video URL to download")
    config: Optional[DownloadConfig] = Field(None, description="Download configuration")

    @field_validator("url")
    def validate_url(cls, v):
        if not v.strip():
            raise ValueError("URL cannot be empty")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "config": {
                    "output_path": "./downloads",
                    "quality": "720p",
                    "extract_audio": True,
                    "audio_format": "mp3",
                },
            }
        }


class SearchRequest(BaseModel):
    """Request model for search endpoints"""

    query: str = Field(..., min_length=1, max_length=200, description="Search query")
    max_results: int = Field(10, ge=1, le=50, description="Maximum number of results")

    class Config:
        json_schema_extra = {"example": {"query": "python tutorial", "max_results": 5}}


class PlaylistRequest(BaseModel):
    """Request model for playlist downloads"""

    url: str = Field(..., description="Playlist URL")
    config: Optional[DownloadConfig] = Field(None, description="Download configuration")
    max_videos: int = Field(
        100, ge=1, le=1000, description="Maximum videos to download"
    )

    @field_validator("url")
    def validate_playlist_url(cls, v):
        if not v.strip():
            raise ValueError("URL cannot be empty")
        if "playlist" not in v.lower():
            raise ValueError("URL must be a playlist URL")
        return v.strip()


class DownloadResponse(BaseModel):
    """Response model for download operations"""

    success: bool
    message: str
    id: str
    filename: Optional[str] = None
    video_info: Optional[VideoInfo] = None
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Download completed successfully",
                "filename": "./downloads/Rick Astley - Never Gonna Give You Up.mp4",
                "video_info": {
                    "title": "Rick Astley - Never Gonna Give You Up",
                    "duration": 212,
                    "uploader": "RickAstleyVEVO",
                },
            }
        }


class SearchResponse(BaseModel):
    """Response model for search operations"""

    success: bool
    message: str
    results: List[VideoInfo] = Field(default_factory=list)
    total_results: int = 0
    error: Optional[str] = None

    def __getitem__(self, item):
        return self.results[item]

    def __len__(self):
        return len(self.results)

    def __iter__(self):
        return iter(self.results)

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Search completed successfully",
                "total_results": 3,
                "results": [
                    {
                        "title": "Python Tutorial for Beginners",
                        "url": "https://www.youtube.com/watch?v=example1",
                        "uploader": "Programming Channel",
                        "duration": 1800,
                    }
                ],
            }
        }


class PlaylistResponse(BaseModel):
    """Response model for playlist operations"""

    success: bool
    message: str
    downloaded_files: List[str] = Field(default_factory=list)
    failed_downloads: List[str] = Field(default_factory=list)
    total_videos: int = 0
    successful_downloads: int = 0
    error: Optional[str] = None

    def __getitem__(self, item):
        return self.downloaded_files[item]

    def __len__(self):
        return len(self.downloaded_files)

    def __iter__(self):
        return iter(self.downloaded_files)


class HealthResponse(BaseModel):
    """Health check response"""

    status: str = "healthy"
    yt_dlp_available: bool = False
    ffmpeg_available: bool = False
    version: str = "1.0.0"
    binaries_path: Optional[str] = None
    error: Optional[str] = None


class StreamInfo(BaseModel):
    index: int
    codec_type: str
    codec_name: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    bit_rate: Optional[int] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    language: Optional[str] = None


class MediaInfo(BaseModel):
    filename: str
    format_name: str
    format_long_name: str
    duration: float
    size: int
    bit_rate: int
    streams: List[StreamInfo]
