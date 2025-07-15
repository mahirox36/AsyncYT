__all__ = [
    "AsyncYTBase",
    "DownloadGotCanceledError",
    "DownloadAlreadyExistsError",
    "DownloadNotFoundError",
    "YtdlpDownloadError",
    "YtdlpSearchError",
    "YtdlpGetInfoError",
    "YtdlpPlaylistGetInfoError",
]


from typing import List, Optional


class AsyncYTBase(Exception):
    """Base exception for all AsyncYT-related errors."""

    pass


class DownloadGotCanceledError(AsyncYTBase):
    """Raised when a download with the given ID got Canceled."""

    def __init__(self, download_id: str):
        message = f"Download with ID '{download_id}' was Got Canceled."
        self.download_id = download_id
        super().__init__(message)


class DownloadAlreadyExistsError(AsyncYTBase):
    """Raised when a download with the given ID already exists."""

    def __init__(self, download_id: str):
        message = f"Download with ID '{download_id}' was already exists."
        self.download_id = download_id
        super().__init__(message)


class DownloadNotFoundError(AsyncYTBase):
    """Raised when a download with the given ID isn't found."""

    def __init__(self, download_id: str):
        message = f"Download with ID '{download_id}' was not found."
        self.download_id = download_id
        super().__init__(message)


class YtdlpDownloadError(AsyncYTBase, RuntimeError):
    """Raised when an error occurs in yt-dlp downloading."""

    def __init__(
        self, url: str, error_code: Optional[int], cmd: List[str], output: List[str]
    ):
        message = f"Download failed for {url}"
        self.error_code = error_code
        self.cmd = " ".join(cmd)
        self.output = "\n".join(output)
        super().__init__(message)


class YtdlpSearchError(AsyncYTBase, RuntimeError):
    """Raised when an error occurs in yt-dlp searching."""

    def __init__(self, query: str, error_code: Optional[int], output: str):
        message = f"Search failed for {query}"
        self.error_code = error_code
        self.output = output
        super().__init__(message)


class YtdlpGetInfoError(AsyncYTBase, RuntimeError):
    """Raised when an error occurs in yt-dlp getting info."""

    def __init__(self, url: str, error_code: Optional[int], output: str):
        message = f"Failed to get video info for {url}"
        self.error_code = error_code
        self.output = output
        super().__init__(message)


class YtdlpPlaylistGetInfoError(AsyncYTBase, RuntimeError):
    """Raised when an error occurs in yt-dlp Playlist getting info."""

    def __init__(self, url: str, error_code: Optional[int], output: str):
        message = f"Failed to get video info for {url}"
        self.error_code = error_code
        self.output = output
        super().__init__(message)
