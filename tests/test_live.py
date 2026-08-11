"""Integration tests against a real Tracearr instance.

Skipped unless TRACEARR_URL and TRACEARR_API_KEY are set. Run with:
    uv run pytest -m integration

The Tracearr public API is read-only, so these tests never write anything --
there is no scratch fixture or cleanup needed.
"""

import os

import pytest
from fastmcp import Client

import tracearr_mcp

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not (os.environ.get("TRACEARR_URL") and os.environ.get("TRACEARR_API_KEY")),
        reason="requires TRACEARR_URL and TRACEARR_API_KEY",
    ),
]


@pytest.fixture(autouse=True)
def configure_client():
    tracearr_mcp._client = tracearr_mcp.build_client(os.environ["TRACEARR_URL"], os.environ["TRACEARR_API_KEY"])
    yield


async def call(name, **kwargs):
    async with Client(tracearr_mcp.mcp) as c:
        return await c.call_tool(name, kwargs)


async def test_get_streams_returns_summary():
    result = await call("tracearr_get_streams")
    assert "summary" in result.data


async def test_get_history_page_one():
    result = await call("tracearr_get_history")
    assert "data" in result.data
    assert "meta" in result.data
    assert result.data["meta"]["nextCursor"] is None or isinstance(result.data["meta"]["nextCursor"], str)


async def test_list_libraries_returns_data():
    result = await call("tracearr_list_libraries")
    assert isinstance(result.data["data"], list)


async def test_list_users_returns_page():
    result = await call("tracearr_list_users")
    assert "meta" in result.data
    assert isinstance(result.data["meta"]["pageSize"], int)


async def test_list_recently_added_returns_page():
    result = await call("tracearr_list_recently_added")
    assert "data" in result.data
    assert "meta" in result.data


async def test_media_endpoints_when_history_exists():
    history = await call("tracearr_get_history", page_size=1)
    records = history.data["data"]
    if not records or not records[0].get("media_id"):
        pytest.skip("no watch history on this instance")
    ref = records[0]["media_id"]

    media = await call("tracearr_get_media", ref=ref)
    assert media.data["id"] == ref

    await call("tracearr_get_media_stats", ref=ref)
    await call("tracearr_get_media_watchers", ref=ref)
    await call("tracearr_get_media_history", ref=ref)
    await call("tracearr_get_media_children", ref=ref)


async def test_user_endpoints_when_users_exist():
    users = await call("tracearr_list_users", page_size=1)
    records = users.data["data"]
    if not records:
        pytest.skip("no users on this instance")
    user_id = records[0]["id"]

    user = await call("tracearr_get_user", id=user_id)
    assert user.data["id"] == user_id

    await call("tracearr_get_user_stats", id=user_id)
    await call("tracearr_get_user_history", id=user_id)
