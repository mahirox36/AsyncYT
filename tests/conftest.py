# tests/conftest.py
import pytest
from asyncyt import Downloader

@pytest.fixture(scope="session")
async def downloader():
    d = Downloader()
    await d.setup_binaries()
    return d
