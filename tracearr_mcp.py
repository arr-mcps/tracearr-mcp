"""MCP server exposing Tracearr's Public API v2 (https://docs.tracearr.com/api) as tools.

One tool per endpoint (see README for the full list). Auth is a bearer
TRACEARR_API_KEY sent as `Authorization: Bearer trr_pub_<token>` -- generate
the key in Tracearr Settings > General. The whole API surface is read-only
(GET), so every tool is marked readOnlyHint and none are destructive.

ponytail: v1 API is not wrapped -- this spec is v2 only (available in Tracearr
2.0.0+). Base path `/api/v2/public` is hardcoded in build_client.
"""

import os
import sys
from typing import Any
from urllib.parse import quote

import httpx
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

READONLY = ToolAnnotations(readOnlyHint=True)

# Tracearr responses are plain JSON. `dict[str, Any]` (not bare `Any`) matters
# here: FastMCP needs a concrete schema to build MCP structured content, and
# skips that step entirely for an `Any` return type -- which silently makes
# Client.call_tool's `.data` come back None for any tool returning a JSON array
# (tracearr_list_libraries and friends). Verified against fastmcp 3.4.6.
JSONObj = dict[str, Any]
JSONVal = JSONObj | list[Any]

mcp = FastMCP("tracearr-mcp")

_client: httpx.AsyncClient | None = None


def build_client(base_url: str, api_key: str | None, transport: httpx.BaseTransport | None = None) -> httpx.AsyncClient:
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    return httpx.AsyncClient(base_url=f"{base_url.rstrip('/')}/api/v2/public", headers=headers, transport=transport)


async def _req(method: str, path: str, params: dict[str, Any] | None = None) -> JSONVal:
    assert _client is not None, "client not configured"
    r = await _client.request(method, path, params=params)
    if r.status_code >= 400:
        try:
            msg = r.json().get("message", r.text)
        except ValueError:
            msg = r.text
        raise ToolError(f"Tracearr API {r.status_code}: {msg}")
    return r.json()


def _ref(ref: str) -> str:
    """URL-encode a media ref, keeping `:` literal so provider refs like
    `movie:tmdb:584` survive. A canonical media uuid passes through untouched."""
    return quote(ref, safe=":")


def _id(id: str) -> str:
    return quote(id)


def _omit(params: dict[str, Any]) -> dict[str, Any]:
    """Drop keys whose values are empty/None so the API's defaults apply."""
    return {k: v for k, v in params.items() if v not in ("", None)}


@mcp.tool(annotations=READONLY)
async def tracearr_get_history(
    cursor: str = "",
    page_size: int = 25,
    user_id: str = "",
    server_id: str = "",
    media_id: str = "",
    rating_key: str = "",
    imdb_id: str = "",
    tmdb_id: int | None = None,
    tvdb_id: int | None = None,
    media_type: str = "",
    watched: bool | None = None,
    since: str = "",
    until: str = "",
) -> JSONObj:
    """Cursor-paginated watch history, newest first, one record per play with
    canonical media identity on every record. A play is one resume chain.

    Filters: user_id (Tracearr identity), server_id, media_id (canonical id;
    a show id matches all its episodes), rating_key (server-specific id),
    imdb_id/tmdb_id/tvdb_id, media_type (movie|episode|track|live|photo|
    unknown), watched (bool), since/until (date or ISO datetime). Pass
    meta.nextCursor back as cursor to fetch the next page."""
    return await _req(
        "GET",
        "/history",
        _omit(
            {
                "cursor": cursor,
                "pageSize": page_size,
                "user_id": user_id,
                "server_id": server_id,
                "media_id": media_id,
                "rating_key": rating_key,
                "imdb_id": imdb_id,
                "tmdb_id": tmdb_id,
                "tvdb_id": tvdb_id,
                "media_type": media_type,
                "watched": watched,
                "since": since,
                "until": until,
            }
        ),
    )


@mcp.tool(annotations=READONLY)
async def tracearr_get_streams(server_id: str = "", summary: bool | None = None) -> JSONObj:
    """Currently active playback sessions across all servers. Each stream
    carries canonical media identity. Set summary=true to return only summary
    stats (omits the data array)."""
    return await _req("GET", "/streams", _omit({"server_id": server_id, "summary": summary}))


@mcp.tool(annotations=READONLY)
async def tracearr_get_media(ref: str) -> JSONObj:
    """Resolve a media ref to its canonical identity, merged ids, and per-server
    availability. ref is a canonical media uuid or a type-qualified provider ref:
    `{movie|show|episode}:{imdb|tmdb|tvdb}:{id}` (e.g. movie:tmdb:584,
    show:tvdb:81189)."""
    return await _req("GET", f"/media/{_ref(ref)}")


@mcp.tool(annotations=READONLY)
async def tracearr_get_media_children(ref: str) -> JSONObj:
    """List a show's seasons (with episode counts) or a season's episodes. ref
    is a canonical media uuid or a provider ref (seasons are uuid-only)."""
    return await _req("GET", f"/media/{_ref(ref)}/children")


@mcp.tool(annotations=READONLY)
async def tracearr_get_media_stats(ref: str) -> JSONObj:
    """Play counts, watch time, and distinct viewers for a media item across
    all_time, last_30, and last_7 windows, each with a combined and per-server
    breakdown. ref is a canonical media uuid or a provider ref."""
    return await _req("GET", f"/media/{_ref(ref)}/stats")


@mcp.tool(annotations=READONLY)
async def tracearr_get_media_watchers(ref: str, window: str = "all_time", server_id: str = "") -> JSONObj:
    """Per-account watchers of a media item, ordered by watch time. window is
    all_time|last_30|last_7 (default all_time). ref is a canonical media uuid
    or a provider ref."""
    return await _req(
        "GET",
        f"/media/{_ref(ref)}/watchers",
        _omit({"window": window, "server_id": server_id}),
    )


@mcp.tool(annotations=READONLY)
async def tracearr_get_media_history(ref: str, cursor: str = "", page_size: int = 25) -> JSONObj:
    """Cursor-paginated watch history for a single media item. ref is a canonical
    media uuid or a provider ref. Pass meta.nextCursor back as cursor."""
    return await _req(
        "GET",
        f"/media/{_ref(ref)}/history",
        _omit({"cursor": cursor, "pageSize": page_size}),
    )


@mcp.tool(annotations=READONLY)
async def tracearr_list_users(cursor: str = "", page_size: int = 25, include_removed: bool | None = None) -> JSONObj:
    """Cursor-paginated Tracearr identities, newest first, each with the
    media-server accounts it owns (account correlation is Tracearr-side).
    Set include_removed=true to include identities whose every account has
    been removed."""
    return await _req(
        "GET",
        "/users",
        _omit({"cursor": cursor, "pageSize": page_size, "include_removed": include_removed}),
    )


@mcp.tool(annotations=READONLY)
async def tracearr_get_user(id: str) -> JSONObj:
    """Resolve a Tracearr identity id to its correlation block (linked accounts
    across servers)."""
    return await _req("GET", f"/users/{_id(id)}")


@mcp.tool(annotations=READONLY)
async def tracearr_get_user_stats(id: str) -> JSONObj:
    """Plays and watch time for an identity, summed across every account it owns,
    over all_time/last_30/last_7 windows, plus its top genres by play count."""
    return await _req("GET", f"/users/{_id(id)}/stats")


@mcp.tool(annotations=READONLY)
async def tracearr_get_user_history(id: str, cursor: str = "", page_size: int = 25) -> JSONObj:
    """Cursor-paginated watch history for an identity, scoped to every account
    it owns. Pass meta.nextCursor back as cursor."""
    return await _req(
        "GET",
        f"/users/{_id(id)}/history",
        _omit({"cursor": cursor, "pageSize": page_size}),
    )


@mcp.tool(annotations=READONLY)
async def tracearr_list_recently_added(
    cursor: str = "",
    page_size: int = 25,
    server_id: str = "",
    library_id: str = "",
    media_type: str = "",
    include_removed: bool | None = None,
) -> JSONObj:
    """Cursor-paginated library items ordered by server-reported added date,
    newest first. Filter by server_id, library_id, media_type (movie|episode|
    season|show|artist|album|track|photo). Set include_removed=true to include
    tombstones."""
    return await _req(
        "GET",
        "/recently-added",
        _omit(
            {
                "cursor": cursor,
                "pageSize": page_size,
                "server_id": server_id,
                "library_id": library_id,
                "media_type": media_type,
                "include_removed": include_removed,
            }
        ),
    )


@mcp.tool(annotations=READONLY)
async def tracearr_list_libraries() -> JSONObj:
    """Per-library rollups: item/movie/episode/show/track counts, total file
    size, and per-resolution counts for each server library."""
    return await _req("GET", "/libraries")


def main() -> None:
    global _client
    url = os.environ.get("TRACEARR_URL")
    if not url:
        print("TRACEARR_URL environment variable is required (e.g. https://tracearr.example.com)", file=sys.stderr)
        raise SystemExit(1)
    _client = build_client(url, os.environ.get("TRACEARR_API_KEY"))
    mcp.run()


if __name__ == "__main__":
    main()
