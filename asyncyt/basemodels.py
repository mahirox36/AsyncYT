from pathlib import Path
from typing import Annotated, Any, Dict, Iterator, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

from .enums import *
from .encoding import EncodingConfig

__all__ = [
    "VideoInfo",
    "DownloadConfig",
    "DownloadProgress",
    "DownloadRequest",
    "DownloadResponse",
    "SearchRequest",
    "SearchResponse",
    "PlaylistVideoInfo",
    "PlaylistInfo",
    "PlaylistConfig",
    "PlaylistRequest",
    "PlaylistDownloadProgress",
    "PlaylistItemResult",
    "PlaylistResponse",
    "DownloadFileProgress",
    "SetupProgress",
    "HealthResponse",
    "InputFile",
    "StreamInfo",
    "MediaInfo",
]



class VideoInfo(BaseModel):
    """
    Video information extracted from URL.

    :param url: Video URL.
    :param title: Video title.
    :param duration: Duration in seconds.
    :param uploader: Uploader name.
    :param view_count: Number of views.
    :param like_count: Number of likes.
    :param description: Video description.
    :param thumbnail: Thumbnail URL.
    :param upload_date: Upload date string (YYYYMMDD).
    :param formats: List of available formats.
    """

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
            url=data.get("webpage_url", data.get("url", "")),
            title=data.get("title", ""),
            duration=data.get("duration", 0) or 0,
            uploader=data.get("uploader", data.get("channel", "")),
            view_count=data.get("view_count", 0) or 0,
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
                "view_count": 1_000_000_000,
                "like_count": 10_000_000,
                "description": "Official video...",
                "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
                "upload_date": "20091025",
            }
        }



class PlaylistVideoInfo(BaseModel):
    """
    Lightweight info for a single video inside a playlist.

    This is populated during ``get_playlist_info`` from yt-dlp's
    ``--flat-playlist`` output, so heavy fields like ``formats`` are absent.
    Use ``get_video_info(entry.url)`` if you need full format data.

    :param id: Video ID (e.g. YouTube video ID).
    :param url: Full video URL.
    :param title: Video title.
    :param duration: Duration in seconds (may be 0 if unavailable flat).
    :param uploader: Channel / uploader name.
    :param thumbnail: Best thumbnail URL available from flat data.
    :param thumbnails: All thumbnail variants returned by yt-dlp.
    :param upload_date: Upload date string (YYYYMMDD).
    :param view_count: View count (may be 0 if unavailable flat).
    :param playlist_index: 1-based position inside the playlist.
    """

    id: str = ""
    url: str
    title: str | None = None
    duration: float = Field(0.0, ge=0)
    uploader: Optional[str] = None
    thumbnail: str | None = None
    thumbnails: List[Dict[str, Any]] = Field(default_factory=list)
    upload_date: str = ""
    view_count: int = Field(0, ge=0)
    playlist_index: Optional[int] = None

    @classmethod
    def from_flat_dict(
        cls, data: dict, index: Optional[int] = None
    ) -> "PlaylistVideoInfo":
        """
        Build a PlaylistVideoInfo from a yt-dlp ``--flat-playlist`` entry.

        :param data: Raw yt-dlp entry dict.
        :param index: 1-based position in the playlist (optional).
        """
        # Prefer the best thumbnail
        thumbnails: List[Dict[str, Any]] = data.get("thumbnails", [])
        thumbnail_url: str = data.get("thumbnail", "")
        if not thumbnail_url and thumbnails:
            # yt-dlp sorts thumbnails by quality; last is usually best
            thumbnail_url = thumbnails[-1].get("url", "")

        raw_url: str = (
            data.get("webpage_url")
            or data.get("url")
            or (
                f"https://www.youtube.com/watch?v={data['id']}"
                if data.get("id")
                else ""
            )
        )

        return cls(
            id=data.get("id", ""),
            url=raw_url,
            title=data.get("title", ""),
            duration=float(data.get("duration", 0) or 0),
            uploader=data.get("uploader")
            or data.get("channel")
            or data.get("uploader_id", ""),
            thumbnail=thumbnail_url,
            thumbnails=thumbnails,
            upload_date=data.get("upload_date", ""),
            view_count=int(data.get("view_count", 0) or 0),
            playlist_index=index,
        )


class PlaylistInfo(BaseModel):
    """
    Full metadata for a playlist, including all video entries.

    :param id: Playlist ID.
    :param url: Playlist URL.
    :param title: Playlist title.
    :param description: Playlist description.
    :param uploader: Channel / uploader name.
    :param thumbnail: Playlist thumbnail URL.
    :param entry_count: Total number of entries in the playlist (may exceed ``entries`` if
                        ``max_videos`` was applied).
    :param entries: List of :class:`PlaylistVideoInfo` objects.
    """

    id: str = ""
    url: str = ""
    title: str = "Unknown Playlist"
    description: Optional[str] = None
    uploader: Optional[str] = None
    thumbnail: Optional[str] = None
    entry_count: int = 0
    entries: List[PlaylistVideoInfo] = Field(default_factory=list)

    def __len__(self) -> int:
        return len(self.entries)

    def __getitem__(self, item: int) -> PlaylistVideoInfo:
        return self.entries[item]

    def __iter__(self) -> Iterator[PlaylistVideoInfo]:  # type: ignore[override]
        return iter(self.entries)

    @classmethod
    def from_ytdlp(
        cls,
        raw_entries: List[dict],
        playlist_url: str,
        max_videos: Optional[int] = None,
    ) -> "PlaylistInfo":
        """
        Build a PlaylistInfo from a list of raw yt-dlp flat-playlist dicts.

        :param raw_entries: Raw list of entry dicts from yt-dlp.
        :param playlist_url: The original playlist URL.
        :param max_videos: Limit to this many entries (None = all).
        """
        total = len(raw_entries)
        if max_videos:
            raw_entries = raw_entries[:max_videos]

        entries = [
            PlaylistVideoInfo.from_flat_dict(e, index=i + 1)
            for i, e in enumerate(raw_entries)
        ]

        # Try to pull playlist-level metadata from the first entry
        first = raw_entries[0] if raw_entries else {}
        pl_title = (
            first.get("playlist_title") or first.get("playlist") or "Unknown Playlist"
        )
        pl_id = first.get("playlist_id", "")
        pl_uploader = (
            first.get("playlist_uploader") or first.get("playlist_channel") or ""
        )
        # Use the best thumbnail from the first video as a proxy
        pl_thumbnail = entries[0].thumbnail

        return cls(
            id=pl_id,
            url=playlist_url,
            title=pl_title,
            uploader=pl_uploader,
            thumbnail=pl_thumbnail,
            entry_count=total,
            entries=entries,
        )


class PlaylistConfig(BaseModel):
    """
    Configuration specific to playlist downloads.

    Extends the concept of :class:`DownloadConfig` at the playlist level,
    letting you control concurrency, item ranges, and failure behaviour without
    duplicating all per-video settings (those live inside ``item_config``).

    :param item_config: Per-video :class:`DownloadConfig` applied to each item.
    :param max_videos: Maximum number of videos to download (0 = all).
    :param start_index: 1-based playlist index to start from.
    :param end_index: 1-based playlist index to stop at (inclusive). ``None`` = end.
    :param concurrency: How many videos to download simultaneously (1 = sequential).
    :param skip_on_error: If True, log failed items and continue; otherwise abort.
    :param reverse: Download playlist in reverse order.
    :param write_playlist_metadata: Write a ``playlist.json`` file with
                                     :class:`PlaylistInfo` metadata alongside the videos.
    """

    item_config: Optional["DownloadConfig"] = Field(
        default=None,
        description="Per-video DownloadConfig applied to each playlist item",
    )
    max_videos: int = Field(
        default=0,
        ge=0,
        description="Maximum videos to download (0 = unlimited)",
    )
    start_index: int = Field(
        default=1,
        ge=1,
        description="1-based playlist index to start downloading from",
    )
    end_index: Optional[int] = Field(
        default=None,
        ge=1,
        description="1-based playlist index to stop at (inclusive)",
    )
    concurrency: int = Field(
        default=1,
        ge=1,
        le=8,
        description="Number of simultaneous video downloads (1 = sequential)",
    )
    skip_on_error: bool = Field(
        default=True,
        description="Continue playlist if a single video fails",
    )
    reverse: bool = Field(
        default=False,
        description="Download in reverse playlist order",
    )
    write_playlist_metadata: bool = Field(
        default=False,
        description="Write a playlist.json metadata file",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "item_config": {
                    "output_path": "./playlist_out",
                    "quality": "1080p",
                    "embed_metadata": True,
                },
                "max_videos": 20,
                "concurrency": 2,
                "skip_on_error": True,
            }
        }


class PlaylistItemResult(BaseModel):
    """
    Result of downloading a single playlist item.

    :param index: 1-based playlist index.
    :param video_info: Video metadata.
    :param success: Whether the download succeeded.
    :param filepath: Final output file path (None if failed).
    :param error: Error message (None if succeeded).
    """

    index: int
    video_info: PlaylistVideoInfo
    success: bool
    filepath: Optional[str] = None
    error: Optional[str] = None


class PlaylistDownloadProgress(BaseModel):
    """
    Real-time progress for a full playlist download operation.

    The ``current_video_progress`` field mirrors a normal
    :class:`DownloadProgress` so callers can render per-video progress bars
    alongside the overall playlist progress.

    :param playlist_id: Unique ID for this playlist download session.
    :param playlist_info: Full playlist metadata (available after fetch stage).
    :param status: High-level playlist status.
    :param total_videos: Total number of videos selected for download.
    :param completed_videos: Number of successfully downloaded videos.
    :param failed_videos: Number of failed videos so far.
    :param current_index: 1-based index of the video currently being processed.
    :param current_video: Metadata of the video currently being downloaded.
    :param current_video_progress: Live :class:`DownloadProgress` for the active video.
    :param overall_percentage: Overall playlist completion 0–100.
    :param results: Completed item results accumulated so far.
    """

    playlist_id: str
    playlist_info: Optional[PlaylistInfo] = None
    status: PlaylistStatus = PlaylistStatus.PENDING
    total_videos: int = 0
    completed_videos: int = 0
    failed_videos: int = 0
    current_index: int = 0
    current_video: Optional[PlaylistVideoInfo] = None
    current_video_progress: Optional["DownloadProgress"] = None
    overall_percentage: Annotated[float, Field(ge=0.0, le=100.0)] = 0.0
    results: List[PlaylistItemResult] = Field(default_factory=list)

    def _recalculate_percentage(self) -> None:
        if self.total_videos > 0:
            done = self.completed_videos + self.failed_videos
            self.overall_percentage = round((done / self.total_videos) * 100, 1)

    class Config:
        json_encoders = {float: lambda v: round(v, 2)}





class DownloadConfig(BaseModel):
    """
    Configuration for a single video download.

    :param output_path: Directory where files are saved.
    :param quality: Desired video quality.
    :param audio_format: Audio container when extracting audio.
    :param video_format: Video container format for remux/recode.
    :param extract_audio: Download audio only.
    :param embed_subs: Embed subtitles into the container.
    :param write_subs: Write subtitle sidecar files.
    :param subtitle_lang: BCP-47 subtitle language code.
    :param write_thumbnail: Download thumbnail as a sidecar file.
    :param embed_thumbnail: Embed thumbnail into the media file.
    :param embed_metadata: Embed title/uploader/etc. metadata.
    :param write_info_json: Write yt-dlp info JSON sidecar.
    :param write_live_chat: Download live chat replay.
    :param custom_filename: Custom yt-dlp output template.
    :param cookies_file: Path to a Netscape cookies file.
    :param proxy: Proxy URL.
    :param rate_limit: Download rate limit (e.g. ``"1M"``, ``"500K"``).
    :param retries: yt-dlp retry count.
    :param fragment_retries: yt-dlp fragment retry count.
    :param custom_options: Extra yt-dlp options passed as ``{key: value}``.
    :param encoding: Fine-grained FFmpeg encoding settings.
    """

    output_path: str = Field(default="./downloads", description="Output directory path")
    quality: Quality = Field(default=Quality.BEST, description="Video quality setting")
    audio_format: Optional[AudioFormat] = Field(
        default=None, description="Audio format for extraction"
    )
    video_format: Optional[VideoFormat] = Field(
        default=None, description="Video container format"
    )
    extract_audio: bool = Field(default=False, description="Extract audio only")
    embed_subs: bool = Field(default=False, description="Embed subtitles in video")
    write_subs: bool = Field(default=False, description="Write subtitle files")
    subtitle_lang: str = Field(default="en", description="Subtitle language code")
    write_thumbnail: bool = Field(default=False, description="Download thumbnail")
    embed_thumbnail: bool = Field(default=False, description="Embed thumbnail")
    embed_metadata: bool = Field(default=True, description="Embed metadata")
    write_info_json: bool = Field(default=False, description="Write info JSON file")
    write_live_chat: bool = Field(default=False, description="Download live chat")
    custom_filename: Optional[str] = Field(
        default=None, description="Custom yt-dlp output template"
    )
    cookies_file: Optional[str] = Field(
        default=None, description="Path to cookies file"
    )
    proxy: Optional[str] = Field(default=None, description="Proxy URL")
    rate_limit: Optional[str] = Field(
        default=None, description="Rate limit e.g. '1M' or '500K'"
    )
    retries: int = Field(default=3, ge=0, le=10, description="Number of retries")
    fragment_retries: int = Field(
        default=3, ge=0, le=10, description="Fragment retries"
    )
    custom_options: Dict[str, Any] = Field(
        default_factory=dict, description="Custom yt-dlp options"
    )
    encoding: Optional[EncodingConfig] = Field(
        default=None,
        description="Fine-grained video/audio encoding settings.",
    )

    @field_validator("output_path")
    def validate_output_path(cls, v):
        Path(v).mkdir(parents=True, exist_ok=True)
        return v

    @field_validator("rate_limit")
    def validate_rate_limit(cls, v):
        if v and not any(v.endswith(u) for u in ["K", "M", "G", "k", "m", "g"]):
            if not v.isdigit():
                raise ValueError("Rate limit must be a number or end with K/M/G")
        return v

    @model_validator(mode="after")
    def handle_extract_audio(self) -> "DownloadConfig":
        if self.extract_audio:
            self.embed_subs = False
        return self

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "output_path": "./downloads",
                "quality": "1080p",
                "video_format": "mp4",
                "extract_audio": False,
                "encoding": {
                    "video": {"codec": "libx264", "crf": 20, "preset": "slow"},
                    "audio": {"codec": "aac", "bitrate": "192k"},
                },
                "embed_thumbnail": True,
                "embed_metadata": True,
            }
        }



class DownloadProgress(BaseModel):
    """
    Real-time progress for a single video download.

    During FFmpeg encode/remux, the ``encoding_*`` fields are populated from
    FFmpeg's ``-progress pipe:1`` output, which AsyncYT parses in real-time
    by using ``--external-downloader ffmpeg`` with custom args.

    :param id: Download ID (SHA-256 of URL + config).
    :param url: Source URL.
    :param title: Video title (filled once yt-dlp reports it).
    :param status: Current phase.
    :param downloaded_bytes: Bytes received so far.
    :param total_bytes: Expected total bytes.
    :param speed: Download speed string, e.g. ``"3.20MiB/s"``.
    :param eta: Estimated remaining seconds during download.
    :param percentage: Overall download progress 0–100.
    :param encoding_percentage: FFmpeg encode progress 0–100.
    :param encoding_fps: Frames per second during encode.
    :param encoding_speed: Encoding speed multiplier, e.g. ``"2.50x"``.
    :param encoding_frame: Current frame being encoded.
    :param encoding_bitrate: Output bitrate during encode, e.g. ``"2048kbits/s"``.
    :param encoding_size: Output size so far, e.g. ``"4096KiB"``.
    :param encoding_time: Elapsed encode time as ``HH:MM:SS.mmm``.
    """

    id: str
    url: str
    title: str = ""
    status: ProgressStatus = ProgressStatus.DOWNLOADING
    downloaded_bytes: int = 0
    total_bytes: int = 0
    speed: str = ""
    eta: int = 0
    percentage: Annotated[float, Field(ge=0.0, le=100.0)] = 0.0

    # Encoding / remux phase (populated from FFmpeg -progress pipe:1)
    encoding_percentage: Annotated[float, Field(ge=0.0, le=100.0)] = 0.0
    encoding_fps: Optional[float] = None
    encoding_speed: Optional[str] = None
    encoding_frame: Optional[int] = None
    encoding_bitrate: Optional[str] = None
    encoding_size: Optional[str] = None
    encoding_time: Optional[str] = None

    @property
    def is_complete(self) -> bool:
        return self.status == ProgressStatus.COMPLETED

    class Config:
        json_encoders = {float: lambda v: round(v, 2)}



class DownloadFileProgress(BaseModel):
    """Progress for binary file downloads (yt-dlp / ffmpeg setup)."""

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
    """Progress for binary setup (yt-dlp / ffmpeg download)."""

    file: str = "yt-dlp"
    download_file_progress: DownloadFileProgress = Field(
        description="Progress of the file being downloaded"
    )

    class Config:
        json_encoders = {float: lambda v: round(v, 2)}


class DownloadRequest(BaseModel):
    """Request model for single-video download endpoints."""

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
    """Request model for search endpoints."""

    query: str = Field(..., min_length=1, max_length=200, description="Search query")
    max_results: int = Field(10, ge=1, le=50, description="Maximum number of results")

    class Config:
        json_schema_extra = {"example": {"query": "python tutorial", "max_results": 5}}


class PlaylistRequest(BaseModel):
    """
    Request model for playlist download endpoints.

    :param url: Playlist URL.
    :param playlist_config: Playlist-level configuration (concurrency, ranges, etc.).
                            When omitted, sensible defaults are used.
    """

    url: str = Field(..., description="Playlist URL")
    playlist_config: Optional[PlaylistConfig] = Field(
        None,
        description="Playlist download configuration",
    )

    @field_validator("url")
    def validate_playlist_url(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("URL cannot be empty")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.youtube.com/playlist?list=PLxxxxxxx",
                "playlist_config": {
                    "item_config": {"output_path": "./playlist", "quality": "720p"},
                    "max_videos": 10,
                    "concurrency": 2,
                    "skip_on_error": True,
                },
            }
        }


class DownloadResponse(BaseModel):
    """Response model for single-video download operations."""

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
    """Response model for search operations."""

    success: bool
    message: str
    results: List[VideoInfo] = Field(default_factory=list)
    total_results: int = 0
    error: Optional[str] = None

    def __getitem__(self, item):
        return self.results[item]

    def __len__(self):
        return len(self.results)


class PlaylistResponse(BaseModel):
    """
    Response model for playlist download operations.

    :param success: Overall success flag (True even when some items failed if
                    ``skip_on_error`` was enabled and at least one succeeded).
    :param message: Human-readable summary.
    :param playlist_info: Full playlist metadata.
    :param results: Per-item download results.
    :param total_videos: Total number of playlist videos selected.
    :param successful_downloads: Count of successfully downloaded videos.
    :param failed_downloads: Count of failed videos.
    :param downloaded_files: Convenience list of output file paths.
    :param error: Top-level error message (only set when the entire operation failed).
    """

    success: bool
    message: str
    playlist_info: Optional[PlaylistInfo] = None
    results: List[PlaylistItemResult] = Field(default_factory=list)
    total_videos: int = 0
    successful_downloads: int = 0
    failed_downloads: int = 0
    downloaded_files: List[str] = Field(default_factory=list)
    error: Optional[str] = None

    def __getitem__(self, item):
        return self.results[item]

    def __len__(self):
        return len(self.results)



class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    yt_dlp_available: bool = False
    ffmpeg_available: bool = False
    version: str = "1.0.0"
    binaries_path: Optional[str] = None
    error: Optional[str] = None


class InputFile(BaseModel):
    """Single input file configuration."""

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


class StreamInfo(BaseModel):
    """Stream information for media files."""

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
    """Media file information."""

    filename: str
    format_name: str
    format_long_name: str
    duration: float
    size: int
    bit_rate: int
    streams: List[StreamInfo]
