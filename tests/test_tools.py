"""Offline tests: one per Tracearr API endpoint, plus error-path tests.

No network. Each tool call is checked against the exact HTTP request it should
produce (method, path incl. URL-encoding of provider refs, query params) via
httpx.MockTransport, using FastMCP's in-memory Client (see
https://gofastmcp.com/development/tests).
"""

import json

import httpx
import pytest
import pytest_asyncio
from fastmcp import Client
from fastmcp.exceptions import ToolError

import tracearr_mcp


class Recorder:
    """Captures the single request made during a test and replays a canned response."""

    def __init__(self):
        self.method = None
        self.url = None
        self.headers = None
        self.params = None
        self.json = None
        self.response = httpx.Response(200, json={"success": True})

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.method = request.method
        self.url = request.url
        self.headers = request.headers
        self.params = request.url.params
        self.json = json.loads(request.content) if request.content else None
        return self.response


@pytest.fixture
def recorder():
    return Recorder()


@pytest_asyncio.fixture
async def server(recorder, monkeypatch):
    transport = httpx.MockTransport(recorder.handler)
    client = tracearr_mcp.build_client("https://tracearr.example.com", "trr_pub_test-key", transport=transport)
    monkeypatch.setattr(tracearr_mcp, "_client", client)
    yield tracearr_mcp.mcp
    await client.aclose()


async def call(server, name, **kwargs):
    async with Client(server) as c:
        return await c.call_tool(name, kwargs)


# --- one test per endpoint --------------------------------------------------

async def test_1_get_history(server, recorder):
    await call(server, "tracearr_get_history")
    assert recorder.method == "GET"
    assert recorder.url.path == "/api/v2/public/history"


async def test_2_get_streams(server, recorder):
    await call(server, "tracearr_get_streams")
    assert recorder.method == "GET"
    assert recorder.url.path == "/api/v2/public/streams"


async def test_3_get_media(server, recorder):
    await call(server, "tracearr_get_media", ref="movie:tmdb:584")
    assert recorder.method == "GET"
    assert recorder.url.raw_path == b"/api/v2/public/media/movie:tmdb:584"


async def test_4_get_media_children(server, recorder):
    await call(server, "tracearr_get_media_children", ref="show:tvdb:81189")
    assert recorder.url.raw_path == b"/api/v2/public/media/show:tvdb:81189/children"


async def test_5_get_media_stats(server, recorder):
    await call(server, "tracearr_get_media_stats", ref="some-uuid")
    assert recorder.url.path == "/api/v2/public/media/some-uuid/stats"


async def test_6_get_media_watchers(server, recorder):
    await call(server, "tracearr_get_media_watchers", ref="movie:tmdb:584")
    assert recorder.url.path == "/api/v2/public/media/movie:tmdb:584/watchers"
    assert recorder.params["window"] == "all_time"


async def test_7_get_media_history(server, recorder):
    await call(server, "tracearr_get_media_history", ref="movie:tmdb:584")
    assert recorder.url.path == "/api/v2/public/media/movie:tmdb:584/history"


async def test_8_list_users(server, recorder):
    await call(server, "tracearr_list_users")
    assert recorder.method == "GET"
    assert recorder.url.path == "/api/v2/public/users"


async def test_9_get_user(server, recorder):
    await call(server, "tracearr_get_user", id="11111111-1111-1111-1111-111111111111")
    assert recorder.url.path == "/api/v2/public/users/11111111-1111-1111-1111-111111111111"


async def test_10_get_user_stats(server, recorder):
    await call(server, "tracearr_get_user_stats", id="11111111-1111-1111-1111-111111111111")
    assert recorder.url.path == "/api/v2/public/users/11111111-1111-1111-1111-111111111111/stats"


async def test_11_get_user_history(server, recorder):
    await call(server, "tracearr_get_user_history", id="11111111-1111-1111-1111-111111111111")
    assert recorder.url.path == "/api/v2/public/users/11111111-1111-1111-1111-111111111111/history"


async def test_12_list_recently_added(server, recorder):
    await call(server, "tracearr_list_recently_added")
    assert recorder.method == "GET"
    assert recorder.url.path == "/api/v2/public/recently-added"


async def test_13_list_libraries(server, recorder):
    recorder.response = httpx.Response(200, json={"data": []})
    result = await call(server, "tracearr_list_libraries")
    assert recorder.method == "GET"
    assert recorder.url.path == "/api/v2/public/libraries"
    assert result.data == {"data": []}


# --- pagination ---------------------------------------------------------------

async def test_history_sends_page_size_and_cursor(server, recorder):
    await call(server, "tracearr_get_history", cursor="abc", page_size=50)
    assert recorder.params["pageSize"] == "50"
    assert recorder.params["cursor"] == "abc"


async def test_empty_optional_params_are_omitted(server, recorder):
    await call(server, "tracearr_get_history")
    assert "user_id" not in recorder.params
    assert "media_type" not in recorder.params
    assert "since" not in recorder.params
    assert "watched" not in recorder.params


async def test_bool_params_sent_only_when_set(server, recorder):
    await call(server, "tracearr_get_streams", summary=True)
    assert recorder.params["summary"] == "true"

    await call(server, "tracearr_list_recently_added", include_removed=True)
    assert recorder.params["include_removed"] == "true"

    await call(server, "tracearr_list_users")
    assert "include_removed" not in recorder.params


async def test_int_params_sent_only_when_set(server, recorder):
    await call(server, "tracearr_get_history", tmdb_id=27205)
    assert recorder.params["tmdb_id"] == "27205"

    await call(server, "tracearr_get_history")
    assert "tmdb_id" not in recorder.params


# --- auth header --------------------------------------------------------------

async def test_token_sent_as_bearer_header(server, recorder):
    await call(server, "tracearr_list_libraries")
    assert recorder.headers["authorization"] == "Bearer trr_pub_test-key"


async def test_no_token_means_no_authorization_header(recorder, monkeypatch):
    transport = httpx.MockTransport(recorder.handler)
    client = tracearr_mcp.build_client("https://tracearr.example.com", None, transport=transport)
    monkeypatch.setattr(tracearr_mcp, "_client", client)
    await call(tracearr_mcp.mcp, "tracearr_list_libraries")
    assert "authorization" not in recorder.headers
    await client.aclose()


# --- error paths ---------------------------------------------------------------

async def test_404_error_message_reaches_caller(server, recorder):
    recorder.response = httpx.Response(404, json={"message": "No media matches the ref"})
    with pytest.raises(ToolError, match="No media matches the ref"):
        await call(server, "tracearr_get_media", ref="movie:tmdb:999999")


async def test_401_error_surfaces_status(server, recorder):
    recorder.response = httpx.Response(401, json={"message": "Unauthorized"})
    with pytest.raises(ToolError, match="401"):
        await call(server, "tracearr_list_libraries")


async def test_429_rate_limit_surfaces_status(server, recorder):
    recorder.response = httpx.Response(429, json={"message": "Rate limit exceeded"})
    with pytest.raises(ToolError, match="429"):
        await call(server, "tracearr_list_libraries")


async def test_non_json_error_body_does_not_crash(server, recorder):
    recorder.response = httpx.Response(502, text="<html>Bad Gateway</html>")
    with pytest.raises(ToolError, match="502"):
        await call(server, "tracearr_list_libraries")


# --- main() ----------------------------------------------------------------

def test_main_requires_tracearr_url(monkeypatch):
    monkeypatch.delenv("TRACEARR_URL", raising=False)
    with pytest.raises(SystemExit):
        tracearr_mcp.main()
