import inspect
from pathlib import Path
import hashlib

from asyncyt.basemodels import DownloadConfig

__all__ = ["call_callback", "get_unique_filename", "gen_id"]


async def call_callback(callback, *args, **kwargs):
    if inspect.iscoroutinefunction(callback):
        await callback(*args, **kwargs)
    else:
        callback(*args, **kwargs)


def get_unique_filename(file: Path, title: str) -> Path:
    base = file.with_name(title).with_suffix(file.suffix)
    new_file = base
    counter = 1

    while new_file.exists():
        new_file = file.with_name(f"{title} ({counter}){file.suffix}")
        counter += 1

    return new_file


def gen_id(url: str, config: DownloadConfig):
    combined = url + config.model_dump_json()
    return hashlib.sha256(combined.encode()).hexdigest()
