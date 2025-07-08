import pytest_asyncio

@pytest_asyncio.fixture
async def dummy():
    yield 'ok'

async def test_dummy(dummy):
    assert dummy == 'ok'
