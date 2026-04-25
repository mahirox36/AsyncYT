"""
builder.py
------------------
Builds yt-dlp CLI commands from a DownloadConfig.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .basemodels import DownloadConfig

from .enums import AudioFormat, Quality

logger = logging.getLogger(__name__)

__all__ = ["build_download_command"]

_QUALITY_FORMAT: dict[str, str] = {
    Quality.BEST: "bestvideo*+bestaudio/best",
    Quality.WORST: "worstvideo*+worstaudio/worst",
    Quality.AUDIO_ONLY: "bestaudio/best",
    Quality.VIDEO_ONLY: "bestvideo/best",
    Quality.LOW_144P: "bestvideo[height<=144]+bestaudio/best[height<=144]/best",
    Quality.LOW_240P: "bestvideo[height<=240]+bestaudio/best[height<=240]/best",
    Quality.SD_480P: "bestvideo[height<=480]+bestaudio/best[height<=480]/best",
    Quality.HD_720P: "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
    Quality.HD_1080P: "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
    Quality.HD_1440P: "bestvideo[height<=1440]+bestaudio/best[height<=1440]/best",
    Quality.UHD_4K: "bestvideo[height<=2160]+bestaudio/best[height<=2160]/best",
    Quality.UHD_8K: "bestvideo[height<=4320]+bestaudio/best[height<=4320]/best",
}

# Formats that actually exist as source streams on platforms like YouTube.
# Everything else is a *transcoded* output format — we must not filter by
# ext in the -f selector or yt-dlp will find no matching stream and fall
# back to bestaudio, which is usually opus/webm regardless of what you asked for.
_NATIVE_AUDIO_EXTS = frozenset({"m4a", "mp3", "ogg", "opus", "webm", "aac"})

# FFmpeg codec required to produce each lossless/PCM container correctly.
# Without these, FFmpeg silently defaults to opus inside the container.
_AUDIO_FORMAT_CODEC: dict[str, str] = {
    "wav":  "pcm_s16le",
    "flac": "flac",
    "alac": "alac",
    "aiff": "pcm_s16le",
}


def _format_selector(config: "DownloadConfig") -> str:
    quality = str(config.quality)
    if config.extract_audio:
        if config.audio_format and str(config.audio_format) != AudioFormat.COPY:
            fmt = str(config.audio_format)
            # Only restrict by ext when that format actually exists as a
            # source stream; otherwise just fetch bestaudio and let
            # --audio-format handle the transcode.
            if fmt in _NATIVE_AUDIO_EXTS:
                return f"bestaudio[ext={fmt}]/bestaudio/best"
        return "bestaudio/best"
    return _QUALITY_FORMAT.get(quality, "bestvideo*+bestaudio/best")


def build_download_command(
    ytdlp_path: str,
    ffmpeg_path: str,
    url: str,
    config: "DownloadConfig",
) -> List[str]:
    """
    Build a complete yt-dlp CLI command.

    FFmpeg is invoked via ``--external-downloader ffmpeg`` so that its
    ``-progress pipe:1`` output lands on yt-dlp's stdout and can be parsed
    in real-time by AsyncYT's line reader.

    :param ytdlp_path: Path to yt-dlp binary.
    :param ffmpeg_path: Path to ffmpeg binary.
    :param url: Target URL.
    :param config: DownloadConfig instance.
    """
    cmd: List[str] = [ytdlp_path]

    # 1. FFmpeg location
    cmd += ["--ffmpeg-location", ffmpeg_path]

    # 2. Format / quality
    cmd += ["-f", _format_selector(config)]

    # 3. Output template
    output_path = str(Path(config.output_path).resolve())
    if config.custom_filename:
        template = str(Path(output_path) / config.custom_filename)
    else:
        template = str(Path(output_path) / "%(title)s.%(ext)s")
    cmd += ["-o", template]

    # 4. Network / reliability
    if config.proxy:
        cmd += ["--proxy", config.proxy]
    if config.rate_limit:
        cmd += ["-r", config.rate_limit]
    cmd += ["--retries", str(config.retries)]
    cmd += ["--fragment-retries", str(config.fragment_retries)]
    if config.cookies_file:
        cmd += ["--cookies", config.cookies_file]

    # 5. Audio extraction
    if config.extract_audio:
        cmd += ["--extract-audio"]
        if config.audio_format and str(config.audio_format) != AudioFormat.COPY:
            cmd += ["--audio-format", str(config.audio_format)]

    # 6. Container remux / recode
    encoding = getattr(config, "encoding", None)
    if not config.extract_audio and config.video_format:
        vfmt = str(config.video_format)
        needs_reencode = encoding and (
            (encoding.video and encoding.video.codec)
            or (encoding.audio and encoding.audio.codec)
        )
        if needs_reencode:
            cmd += ["--recode-video", vfmt]
        else:
            cmd += ["--remux-video", vfmt]

    # 7. Custom encoding via --postprocessor-args
    #
    #    For audio formats that require a specific FFmpeg codec (wav, flac,
    #    alac, aiff), we inject -c:a so FFmpeg doesn't silently default to
    #    opus.  The user's explicit AudioEncodingConfig.codec always wins;
    #    we only inject the implicit codec when none is set.
    if config.extract_audio:
        audio_fmt = str(config.audio_format) if config.audio_format else None
        implicit_codec = _AUDIO_FORMAT_CODEC.get(audio_fmt or "")

        if encoding is not None:
            # User supplied an EncodingConfig — use it, but patch in the
            # implicit codec if they didn't specify one themselves.
            if implicit_codec and (
                encoding.audio is None or not encoding.audio.codec
            ):
                from .encoding import AudioEncodingConfig
                from .enums import AudioCodec

                patched_audio = (encoding.audio or AudioEncodingConfig()).model_copy(
                    update={"codec": implicit_codec}
                )
                encoding = encoding.model_copy(update={"audio": patched_audio})

            ppa = encoding.build_extract_audio_ppa()
            if ppa:
                cmd += ["--postprocessor-args", ppa]

        elif implicit_codec:
            # No EncodingConfig at all — inject the bare minimum so FFmpeg
            # produces the correct codec inside the container.
            ppa = f"ExtractAudio+ffmpeg_o:-c:a {implicit_codec}"
            cmd += ["--postprocessor-args", ppa]

    else:
        # Video path — only touch postprocessor-args when encoding is set.
        if encoding is not None:
            ppa_vc = encoding.build_video_convertor_ppa()
            if ppa_vc:
                cmd += ["--postprocessor-args", ppa_vc]

            ppa_mg = encoding.build_merger_ppa()
            if ppa_mg:
                cmd += ["--postprocessor-args", ppa_mg]

    # 8. External downloader → FFmpeg with real-time -progress output
    #
    #    We ONLY use --external-downloader ffmpeg when the user has explicitly
    #    requested a re-encode (encoding.video.codec or encoding.audio.codec is
    #    set).  For plain downloads and simple remux/container-change we let
    #    yt-dlp use its built-in downloader so we don't trigger an extra FFmpeg
    #    pass and don't double-encode.
    #
    #    Enabling this unconditionally caused two problems:
    #      1. FFmpeg was invoked even when no encoding was needed (slow, wasteful).
    #      2. A second FFmpeg pass was triggered by yt-dlp postprocessors
    #         (embed-thumbnail, embed-subs, embed-metadata), producing a
    #         double-encode artefact visible in the logs as out_time resetting.
    #
    #    NOTE: we never set --external-downloader for audio-only downloads
    #    because yt-dlp handles extraction via a postprocessor.
    needs_reencode = (
        not config.extract_audio
        and encoding is not None
        and (
            (encoding.video and encoding.video.codec)
            or (encoding.audio and encoding.audio.codec)
        )
    )
    if needs_reencode:
        cmd += ["--external-downloader", "ffmpeg"]
        cmd += [
            "--external-downloader-args",
            "ffmpeg:-progress pipe:1 -loglevel error",
        ]

    # 9. Thumbnail
    if config.write_thumbnail:
        cmd += ["--write-thumbnail"]
    if config.embed_thumbnail:
        cmd += ["--embed-thumbnail"]

    # 10. Subtitles
    if config.embed_subs:
        cmd += ["--embed-subs"]
    if config.write_subs:
        cmd += ["--write-subs"]
    if config.embed_subs or config.write_subs:
        cmd += ["--sub-langs", config.subtitle_lang]

    # 11. Metadata
    if config.embed_metadata:
        cmd += ["--embed-metadata"]

    # 12. Misc
    if config.write_info_json:
        cmd += ["--write-info-json"]
    if config.write_live_chat:
        cmd += ["--write-subs", "--sub-format", "json3"]

    # 13. Overwrite behaviour
    overwrite = getattr(encoding, "overwrite", False) if encoding else False
    if overwrite:
        cmd += ["--force-overwrites"]
    else:
        cmd += ["--no-overwrites"]

    # 14. Progress output (newline mode for easy line-by-line parsing)
    cmd += ["--newline"]

    # 15. Custom yt-dlp options
    for key, value in (config.custom_options or {}).items():
        flag = f"--{key.replace('_', '-')}"
        if value is True:
            cmd.append(flag)
        elif value is not False:
            cmd += [flag, str(value)]

    # 16. URL (always last)
    cmd.append(url)

    logger.debug("yt-dlp command: %s", " ".join(cmd))
    return cmd