__all__ = [
    "AsyncYTBase",
    "FFmpegBase",
    "DownloaderBase",
    "YtDlpBase",
    "InvalidFFmpegConfigError",
    "FFmpegProcessingError",
    "FFmpegOutputExistsError",
    "CodecCompatibilityError",
    "DownloadGotCanceledError",
    "DownloadAlreadyExistsError",
    "DownloadNotFoundError",
    "YtdlpDownloadError",
    "YtdlpSearchError",
    "YtdlpGetInfoError",
    "YtdlpPlaylistGetInfoError",
]


from typing import List, Optional, Union

from asyncyt.utils import suggest_audio_compatible_formats, suggest_compatible_formats

from .enums import AudioFormat, VideoCodec, AudioCodec, VideoFormat


class AsyncYTBase(Exception):
    """Base exception for all AsyncYT-related errors."""

    pass


class FFmpegBase(AsyncYTBase):
    """Base exception for all FFmpeg-related errors."""

    pass


class DownloaderBase(AsyncYTBase):
    """Base exception for all Downloader-related errors."""

    pass


class YtDlpBase(AsyncYTBase):
    """Base exception for all YTdlp-related errors."""

    pass


class InvalidFFmpegConfigError(FFmpegBase):
    """Raised when the provided FFmpeg configuration is invalid or unsupported."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class FFmpegProcessingError(FFmpegBase, RuntimeError):
    """Raised when FFmpeg fails to process the given input file."""

    def __init__(
        self,
        input_file: str,
        error_code: Optional[int],
        cmd: List[str],
        output: List[str] | str,
    ):
        message = f"FFmpeg processing failed for input: {input_file}"
        self.file = input_file
        self.error_code = error_code
        self.cmd = " ".join(cmd)
        self.output = "\n".join(output)
        super().__init__(message)


class FFmpegOutputExistsError(FFmpegBase, RuntimeError):
    """Raised when FFmpeg refuses to overwrite an existing output file."""

    def __init__(self, output: str):
        message = f"Output file already exists and will not be overwritten: {output}."
        self.output = output
        super().__init__(message)


class CodecCompatibilityError(FFmpegBase, RuntimeError):
    """
    Raised when the specified codec(s) are incompatible or unsupported by FFmpeg
    for the given input/output formats or settings.
    """

    def __init__(
        self,
        codec: VideoCodec | AudioCodec,
        format: VideoFormat,
    ):
        self.suggested_format = (
            suggest_compatible_formats(codec)
            if isinstance(codec, VideoCodec)
            else suggest_audio_compatible_formats(codec)
        )
        message = (
            f"Codec compatibility error: '{codec}' is not incompatible on {format}.\n"
            f"Try one of: {self.suggested_format}."
        )
        self.codec = codec
        self.format = format
        super().__init__(message)


class DownloadGotCanceledError(DownloaderBase):
    """Raised when a download with the given ID got canceled."""

    def __init__(self, download_id: str):
        message = f"Download with ID '{download_id}' got canceled."
        self.download_id = download_id
        super().__init__(message)


class DownloadAlreadyExistsError(DownloaderBase):
    """Raised when a download with the given ID already exists."""

    def __init__(self, download_id: str):
        message = f"Download with ID '{download_id}' already exists."
        self.download_id = download_id
        super().__init__(message)


class DownloadNotFoundError(DownloaderBase):
    """Raised when a download with the given ID isn't found."""

    def __init__(self, download_id: str):
        message = f"Download with ID '{download_id}' was not found."
        self.download_id = download_id
        super().__init__(message)


class YtdlpDownloadError(YtDlpBase, RuntimeError):
    """Raised when an error occurs in yt-dlp downloading."""

    def __init__(
        self, url: str, error_code: Optional[int], cmd: List[str], output: List[str]
    ):
        message = f"Download failed for {url}"
        self.error_code = error_code
        self.cmd = " ".join(cmd)
        self.output = "\n".join(output)
        super().__init__(message)


class YtdlpSearchError(YtDlpBase, RuntimeError):
    """Raised when an error occurs in yt-dlp searching."""

    def __init__(self, query: str, error_code: Optional[int], output: str):
        message = f"Search failed for {query}"
        self.error_code = error_code
        self.output = output
        super().__init__(message)


class YtdlpGetInfoError(YtDlpBase, RuntimeError):
    """Raised when an error occurs in yt-dlp getting info."""

    def __init__(self, url: str, error_code: Optional[int], output: str):
        message = f"Failed to get video info for {url}"
        self.error_code = error_code
        self.output = output
        super().__init__(message)


class YtdlpPlaylistGetInfoError(YtDlpBase, RuntimeError):
    """Raised when an error occurs while retrieving playlist info with yt-dlp."""

    def __init__(self, url: str, error_code: Optional[int], output: str):
        message = f"Failed to get video info for {url}"
        self.error_code = error_code
        self.output = output
        super().__init__(message)
