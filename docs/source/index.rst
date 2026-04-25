========
AsyncYT
========

.. image:: https://img.shields.io/pypi/v/asyncyt?style=for-the-badge
   :alt: PyPI - Version

.. image:: https://img.shields.io/pypi/dm/asyncyt?style=for-the-badge
   :alt: Downloads

.. image:: https://img.shields.io/pypi/l/asyncyt?style=for-the-badge
   :alt: License

**AsyncYT** is a fully async, high-performance media downloader for 1000+ websites powered by `yt-dlp <https://github.com/yt-dlp/yt-dlp>`_ and ``ffmpeg``.
It comes with auto binary setup, progress tracking, playlist support, search, and clean API models using ``pydantic``.

Features
========

* ✅ **Fully Async Architecture** – every operation is non‑blocking and ``await``‑ready.
* 🎥 **Video, Audio, and Playlist Support** – download any media you throw at it.
* 🌐 **Automatic Binary Management** – downloads ``yt-dlp`` and ``ffmpeg`` automatically if not found, with update support and resume-capable downloads.
* 🎛 **Rich FFmpeg Encoding Configuration** – control video/audio codecs, CRF, bitrates, presets, pixel formats, scale, FPS, VBV, and more via the new ``EncodingConfig`` model — translated directly into yt-dlp ``--postprocessor-args`` flags, no separate FFmpeg process needed.
* 📡 **Real‑Time Progress Tracking** – granular download *and* FFmpeg encoding progress (percentage, FPS, speed multiplier, bitrate, frame count, elapsed time), perfect for UI updates or WebSockets.
* 🔀 **Smart Postprocessor Routing** – encoding args are automatically routed to the right yt-dlp postprocessor (``VideoConvertor``, ``ExtractAudio``, ``Merger``, ``VideoRemuxer``) depending on your config.
* 🔁 **Resilient Downloads** – configurable retries, fragment retries, rate limiting, proxy support, cookies, and resume-capable binary downloads with exponential back-off.
* 🔍 **Video & Playlist Info** – retrieve full metadata (title, duration, uploader, view/like count, formats, thumbnail) before downloading.
* 🔎 **Built-in Search** – search YouTube directly and get back typed ``VideoInfo`` results.
* 🛡 **Strongly Typed Models** – every input and output is a validated ``pydantic`` model with schema extras and field-level docs.
* 📚 **Rich Enum Library** – type-safe enums for qualities, codecs, presets, pixel formats, audio channels, subtitle formats, progress statuses, and more.
* 🧩 **Clean Exception Hierarchy** – specific exceptions for every failure mode (download canceled, already exists, not found, yt-dlp errors, etc.).
* 🔗 **URL Cleaning Utilities** – normalises YouTube watch, ``youtu.be``, ``/shorts/``, and ``/embed/`` URLs automatically.
* 📂 **Safe File Management** – unique filename generation, overwrite control, and atomic temp-dir → output-dir moves.
* 🖥 **Cross-Platform** – Windows, macOS, and Linux; correct binaries are selected per platform automatically.

Requirements
============

* Python 3.11+
* Cross-platform – Windows, macOS, Linux
* Optional: ``yt-dlp`` and ``ffmpeg`` (auto-downloaded if not present)

Installation
============

.. code-block:: bash

   pip install asyncyt

Quick Start
===========

.. code-block:: python

   import asyncio
   from asyncyt import AsyncYT, DownloadConfig, Quality
   from asyncyt.exceptions import AsyncYTBase

   async def main():
       downloader = AsyncYT()
       await downloader.setup_binaries()

       config = DownloadConfig(quality=Quality.HD_720P)

       info = await downloader.get_video_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
       print(f"Downloading: {info.title}")

       filename = await downloader.download(info.url, config)
       print(f"Downloaded to: {filename}")

   asyncio.run(main())

Encoding Configuration
======================

AsyncYT exposes a rich ``EncodingConfig`` model that gives you full control over how FFmpeg processes your media. It maps directly onto yt-dlp's ``--postprocessor-args`` / ``--ppa`` flags — no extra FFmpeg invocations.

.. code-block:: python

   from asyncyt import AsyncYT, DownloadConfig, Quality, VideoFormat
   from asyncyt.encoding import EncodingConfig, VideoEncodingConfig, AudioEncodingConfig
   from asyncyt.enums import VideoCodec, AudioCodec, Preset, PixelFormat

   config = DownloadConfig(
       quality=Quality.HD_1080P,
       video_format=VideoFormat.MP4,
       embed_metadata=True,
       embed_thumbnail=True,
       encoding=EncodingConfig(
           video=VideoEncodingConfig(
               codec=VideoCodec.H264,
               crf=20,
               preset=Preset.SLOW,
               pixel_format=PixelFormat.YUV420P,
           ),
           audio=AudioEncodingConfig(
               codec=AudioCodec.AAC,
               bitrate="192k",
           ),
           overwrite=True,
       ),
   )

Supported Sites
===============

AsyncYT supports **1000+ websites** through yt-dlp, including:

* YouTube, YouTube Music
* Twitch, TikTok, Instagram
* Twitter, Reddit, Facebook
* Vimeo, Dailymotion, and many more

`See full list of supported sites <https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md>`_

---

Contents:
---------

.. toctree::
   :maxdepth: 2

   asyncyt.core
   asyncyt.basemodels
   asyncyt.binaries
   asyncyt.builder
   asyncyt.encoding
   asyncyt.enums
   asyncyt.exceptions
   asyncyt.utils
   genindex
