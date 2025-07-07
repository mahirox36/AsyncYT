from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from .enums import AudioFormat, VideoFormat, Quality

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
]


class VideoInfo(BaseModel):
    """Video information extracted from URL"""

    url: str
    title: str
    duration: float = Field(0, ge=0)
    uploader: str
    view_count: int = Field(0, ge=0)
    like_count: Optional[int] = Field(None, ge=0)
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

    url: str
    title: str = ""
    status: str = "downloading"
    downloaded_bytes: int = 0
    total_bytes: int = 0
    speed: str = ""
    eta: int = 0
    percentage: float = Field(0.0, ge=0.0, le=100.0)

    @property
    def is_complete(self) -> bool:
        return self.status == "finished"

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


class HealthResponse(BaseModel):
    """Health check response"""

    status: str = "healthy"
    yt_dlp_available: bool = False
    ffmpeg_available: bool = False
    version: str = "1.0.0"
    binaries_path: Optional[str] = None
    error: Optional[str] = None
