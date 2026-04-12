__all__ = [
    "AsyncYTBase",
    "DownloaderBase",
    "YtDlpBase",
    "DownloadGotCanceledError",
    "DownloadAlreadyExistsError",
    "DownloadNotFoundError",
    "YtdlpDownloadError",
    "YtdlpSearchError",
    "YtdlpGetInfoError",
    "YtdlpPlaylistGetInfoError",
    "PlaylistDownloadError",
    "PlaylistCancelledError",
]


from typing import List, Optional


class AsyncYTBase(Exception):
    """Base exception for all AsyncYT-related errors."""

    pass


class DownloaderBase(AsyncYTBase):
    """Base exception for all Downloader-related errors."""

    pass


class YtDlpBase(AsyncYTBase):
    """Base exception for all YTdlp-related errors."""

    pass


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
        message = f"Failed to get playlist info for {url}"
        self.error_code = error_code
        self.output = output
        super().__init__(message)


class PlaylistDownloadError(DownloaderBase):
    """Raised when a playlist download fails entirely."""

    def __init__(self, url: str, reason: str):
        message = f"Playlist download failed for '{url}': {reason}"
        self.url = url
        self.reason = reason
        super().__init__(message)


class PlaylistCancelledError(DownloaderBase):
    """Raised when an in-progress playlist download is cancelled."""

    def __init__(self, playlist_id: str, completed: int, total: int):
        message = (
            f"Playlist '{playlist_id}' was cancelled after "
            f"{completed}/{total} videos."
        )
        self.playlist_id = playlist_id
        self.completed = completed
        self.total = total
        super().__init__(message)
