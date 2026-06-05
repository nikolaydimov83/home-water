import os
import tempfile

import pytest
from tortoise import Tortoise

import config


@pytest.fixture
async def app():
    await Tortoise.close_connections()

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    original_db = config.DB_PATH
    config.DB_PATH = tmp.name

    from controller import create_app

    app = await create_app()
    yield app

    await Tortoise.close_connections()
    tmp.close()
    os.unlink(tmp.name)
    config.DB_PATH = original_db
