"""
encoding.py
------------------
Rich encoding configuration models for AsyncYT.
"""

from __future__ import annotations

from typing import Annotated, List, Optional, Union
from pydantic import BaseModel, Field, model_validator

from .enums import (
    AudioChannels,
    AudioCodec,
    PixelFormat,
    Preset,
    TuneOption,
    VideoCodec,
)

__all__ = [
    "VideoEncodingConfig",
    "AudioEncodingConfig",
    "EncodingConfig",
]


class VideoEncodingConfig(BaseModel):
    """
    Fine-grained video encoding settings.

    All values are optional — only set ones are forwarded to FFmpeg via
    yt-dlp's ``--postprocessor-args`` / ``--ppa`` mechanism.

    :param codec: FFmpeg video codec (e.g. ``libx264``, ``hevc_nvenc``).
    :param crf: Constant Rate Factor — quality vs. size (0 = lossless, 51 = worst).
                Not valid for hardware encoders; ignored automatically when
                ``bitrate`` is set (CRF and CBR are mutually exclusive).
    :param bitrate: Target video bitrate, e.g. ``"2M"``, ``"800k"``.
    :param maxrate: Maximum bitrate cap (used with ``bufsize`` for VBV).
    :param bufsize: VBV buffer size, e.g. ``"4M"``.
    :param preset: Encoding speed preset (ultrafast … placebo).
    :param tune: x264/x265 tune option (film, animation, grain …).
    :param pixel_format: Output pixel format (yuv420p, yuv420p10le …).
    :param width: Output width in pixels (keeps aspect ratio when height omitted).
    :param height: Output height in pixels (keeps aspect ratio when width omitted).
    :param fps: Force output frame-rate, e.g. ``30``, ``23.976``.
    :param extra_args: Raw FFmpeg video args appended verbatim, e.g.
                       ``["-profile:v", "high", "-level", "4.1"]``.
    """

    codec: Annotated[Optional[VideoCodec], Field(description="Video codec")] = None

    crf: Annotated[
        Optional[int],
        Field(
            ge=0,
            le=63,
            description="Constant Rate Factor (0=lossless, typical 18-28 for x264)",
        ),
    ] = None

    bitrate: Annotated[
        Optional[str], Field(description="Target video bitrate e.g. '2M'")
    ] = None

    maxrate: Annotated[
        Optional[str], Field(description="Max bitrate cap e.g. '4M'")
    ] = None

    bufsize: Annotated[
        Optional[str], Field(description="VBV buffer size e.g. '8M'")
    ] = None

    preset: Annotated[Optional[Preset], Field(description="Encoding speed preset")] = (
        None
    )

    tune: Annotated[
        Optional[TuneOption], Field(description="x264/x265 tune option")
    ] = None

    pixel_format: Annotated[
        Optional[PixelFormat], Field(description="Output pixel format")
    ] = None

    width: Annotated[
        Optional[int], Field(gt=0, description="Output width in pixels")
    ] = None

    height: Annotated[
        Optional[int], Field(gt=0, description="Output height in pixels")
    ] = None

    fps: Annotated[
        Optional[Union[int, float]], Field(gt=0, description="Output frame rate")
    ] = None

    extra_args: Annotated[
        List[str],
        Field(
            default_factory=list, description="Raw FFmpeg video args appended verbatim"
        ),
    ] = Field(default_factory=list)

    @model_validator(mode="after")
    def _crf_bitrate_exclusive(self) -> "VideoEncodingConfig":
        if self.crf is not None and self.bitrate is not None:
            raise ValueError(
                "crf and bitrate are mutually exclusive — use one or the other."
            )
        return self

    def to_ffmpeg_args(self) -> List[str]:
        """Produce a flat list of FFmpeg CLI args from this config."""
        args: List[str] = []

        if self.codec:
            args += ["-c:v", str(self.codec)]

        if self.crf is not None:
            # -crf works for libx264, libx265, libvpx-vp9, libaom-av1 etc.
            args += ["-crf", str(self.crf)]

        if self.bitrate:
            args += ["-b:v", self.bitrate]

        if self.maxrate:
            args += ["-maxrate", self.maxrate]

        if self.bufsize:
            args += ["-bufsize", self.bufsize]

        if self.preset:
            args += ["-preset", str(self.preset)]

        if self.tune:
            args += ["-tune", str(self.tune)]

        if self.pixel_format:
            args += ["-pix_fmt", str(self.pixel_format)]

        # Scale filter — compose a single -vf scale= expression
        if self.width or self.height:
            w = str(self.width) if self.width else "-1"
            h = str(self.height) if self.height else "-1"
            args += ["-vf", f"scale={w}:{h}"]

        if self.fps is not None:
            args += ["-r", str(self.fps)]

        args += self.extra_args
        return args

    class Config:
        use_enum_values = True


class AudioEncodingConfig(BaseModel):
    """
    Fine-grained audio encoding settings.

    :param codec: FFmpeg audio codec (e.g. ``aac``, ``libmp3lame``, ``libopus``).
    :param bitrate: Target audio bitrate, e.g. ``"192k"``, ``"320k"``.
    :param quality: VBR quality (codec-specific scale, e.g. 0-9 for libmp3lame).
    :param sample_rate: Output sample rate in Hz, e.g. ``44100``, ``48000``.
    :param channels: Number of output channels (``"1"`` mono, ``"2"`` stereo …).
    :param extra_args: Raw FFmpeg audio args appended verbatim.
    """

    codec: Annotated[Optional[AudioCodec], Field(description="Audio codec")] = None

    bitrate: Annotated[
        Optional[str], Field(description="Audio bitrate e.g. '192k'")
    ] = None

    quality: Annotated[
        Optional[int],
        Field(
            ge=0,
            le=10,
            description="VBR quality (libmp3lame: 0=best…9=worst; libopus: ignored; aac: 0-5)",
        ),
    ] = None

    sample_rate: Annotated[
        Optional[int], Field(description="Output sample rate in Hz")
    ] = None

    channels: Annotated[
        Optional[AudioChannels], Field(description="Output channel count")
    ] = None

    extra_args: Annotated[
        List[str],
        Field(
            default_factory=list, description="Raw FFmpeg audio args appended verbatim"
        ),
    ] = Field(default_factory=list)

    def to_ffmpeg_args(self) -> List[str]:
        """Produce a flat list of FFmpeg CLI args from this config."""
        args: List[str] = []

        if self.codec:
            args += ["-c:a", str(self.codec)]

        if self.bitrate:
            args += ["-b:a", self.bitrate]

        if self.quality is not None:
            args += ["-q:a", str(self.quality)]

        if self.sample_rate is not None:
            args += ["-ar", str(self.sample_rate)]

        if self.channels:
            args += ["-ac", str(self.channels)]

        args += self.extra_args
        return args

    class Config:
        use_enum_values = True


class EncodingConfig(BaseModel):
    """
    Combined video + audio encoding settings, plus container-level options.

    Attach this to ``DownloadConfig.encoding`` to get full control over how
    yt-dlp invokes FFmpeg for remuxing/re-encoding.

    :param video: Video encoding settings.
    :param audio: Audio encoding settings.
    :param overwrite: Pass ``-y`` to FFmpeg (overwrite existing files).
    :param extra_global_args: Raw args added before input inside the ``--ppa`` value,
                              e.g. ``["-threads", "4"]``.

    **How it maps to yt-dlp flags**

    AsyncYT translates ``EncodingConfig`` into yt-dlp CLI flags:

    * ``--recode-video FORMAT`` — when a target container is set (inferred from
      ``DownloadConfig.video_format``).
    * ``--postprocessor-args "VideoConvertor+ffmpeg_o:-c:v … -c:a … -crf …"``
      — all encoding args are injected via the ``VideoConvertor`` postprocessor
      so they apply only during the re-encode step, not the merge step.
    * ``--postprocessor-args "ExtractAudio+ffmpeg_o:-c:a …"`` — similarly for
      audio-only downloads.
    * ``--postprocessor-args "Merger+ffmpeg_i1:-v quiet"`` etc. for other PPs.
    """

    video: Annotated[
        Optional[VideoEncodingConfig], Field(None, description="Video encoding")
    ] = None
    audio: Annotated[
        Optional[AudioEncodingConfig], Field(None, description="Audio encoding")
    ] = None
    overwrite: Annotated[
        bool, Field(False, description="Overwrite existing output files (-y)")
    ] = False
    extra_global_args: List[str] = Field(
        default_factory=list,
        description="Extra FFmpeg global args (e.g. ['-threads', '4'])",
    )

    def build_video_convertor_ppa(self) -> Optional[str]:
        """
        Build a ``--postprocessor-args`` value for the ``VideoConvertor`` PP.

        Returns ``None`` if there are no encoding args to inject.
        """
        args: List[str] = list(self.extra_global_args)

        if self.video:
            args += self.video.to_ffmpeg_args()
        if self.audio:
            args += self.audio.to_ffmpeg_args()
        if self.overwrite:
            args += ["-y"]

        if not args:
            return None

        return "VideoConvertor+ffmpeg_o:" + " ".join(args)

    def build_extract_audio_ppa(self) -> Optional[str]:
        """
        Build a ``--postprocessor-args`` value for the ``ExtractAudio`` PP.
        """
        args: List[str] = list(self.extra_global_args)

        if self.audio:
            args += self.audio.to_ffmpeg_args()
        if self.overwrite:
            args += ["-y"]

        if not args:
            return None

        return "ExtractAudio+ffmpeg_o:" + " ".join(args)

    def build_merger_ppa(self) -> Optional[str]:
        """
        Build a ``--postprocessor-args`` value for the ``Merger`` PP.
        Only injects extra global args (the merger just muxes, no re-encode).
        """
        args: List[str] = list(self.extra_global_args)
        if self.overwrite:
            args += ["-y"]
        if not args:
            return None
        return "Merger+ffmpeg_o:" + " ".join(args)

    class Config:
        use_enum_values = True
