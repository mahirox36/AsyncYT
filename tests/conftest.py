# tests/conftest.py
import pytest
from asyncyt import AsyncYT


@pytest.fixture(scope="session")
async def downloader():
    d = AsyncYT()
    await d.setup_binaries()
    return d
