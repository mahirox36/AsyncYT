# API Reference

## Downloader

The main class for all operations.

### Methods

- `await setup_binaries()` – Download yt-dlp and ffmpeg if needed.
- `await get_video_info(url: str) -> VideoInfo` – Get info about a video.
- `await download(url: str, config: DownloadConfig = None, progress_callback = None) -> str` – Download a video.
- `await search(query: str, max_results: int = 10) -> List[VideoInfo]` – Search YouTube.
- `await download_with_response(request: DownloadRequest, progress_callback = None) -> DownloadResponse` – Download with API-style response.
- `await search_with_response(request: SearchRequest) -> SearchResponse` – Search with API-style response.
- `await download_playlist_with_response(request: PlaylistRequest, progress_callback = None) -> PlaylistResponse` – Download a playlist with API-style response.
- `await health_check() -> HealthResponse` – Check if binaries are available.

## DownloadConfig

Configuration for downloads. See [Configuration](./config.md) for all options.

## Models

- `VideoInfo` – Video metadata.
- `DownloadProgress` – Progress info for downloads.
- `DownloadRequest`, `SearchRequest`, `PlaylistRequest` – Request models for API endpoints.
- `DownloadResponse`, `SearchResponse`, `PlaylistResponse`, `HealthResponse` – Response models.

---

See [Examples](./examples.md) for real-world code.
