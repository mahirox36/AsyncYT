from os.path import join
from asyncyt import (
    Downloader,
    DownloadConfig,
    DownloadProgress,
    Quality,
    DownloadRequest,
    VideoFormat
)
from asyncio import run


async def main() -> None:
    print("Doing init thingy...")
    downloader = Downloader()
    await downloader.setup_binaries()
    link = input("Enter a URL\n--> ")
    if not link.startswith("http"):
        print("Please put a Valid URL.")
        return await main()

    config = DownloadConfig(quality=Quality.BEST, video_format=VideoFormat.MP4)
    download_request = DownloadRequest(url=link, config=config)

    async def progress_print(progress: DownloadProgress):
        print(
            f"Downloading at {progress.speed} {progress.downloaded_bytes}/{progress.total_bytes} ({progress.percentage}) eta: {progress.eta}"
        )

    response = await downloader.download_with_response(download_request, progress_print)
    if response.success and response.filename:
        print(
            f"Your File has been downloaded in {join(config.output_path, response.filename)}"
        )


run(main())
