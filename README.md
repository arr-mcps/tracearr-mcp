# tracearr-mcp

Part of the [arr-mcps](https://github.com/arr-mcps/arr-mcps) collection.
MCP server exposing [Tracearr](https://docs.tracearr.com/api)'s Public API v2
(REST, read-only) as tools, so an LLM can query your Plex, Jellyfin, and Emby
monitoring data: watch history, active streams, media, users, libraries, and
recently added items.

Built with [FastMCP](https://gofastmcp.com).

## Enabling the API on your Tracearr server

The Public API is read-only and requires a bearer API key. Generate one in
Tracearr **Settings > General** — the key looks like `trr_pub_<token>`. See
the [API reference](https://docs.tracearr.com/api) for details.

## Install

Download a wheel from the [latest release](https://github.com/arr-mcps/tracearr-mcp/releases/latest)
and install it as a `uv` tool (no repo checkout needed):

```bash
uv tool install tracearr_mcp-*.whl
```

This puts a `tracearr-mcp` command on your PATH. Register it with Claude Code:

```bash
claude mcp add tracearr \
  --env TRACEARR_URL=https://your-tracearr-host \
  --env TRACEARR_API_KEY=<key> \
  -- tracearr-mcp
```

### From source

```bash
uv sync
cp .env.example .env   # fill in TRACEARR_URL and TRACEARR_API_KEY
```

```bash
claude mcp add tracearr \
  --env TRACEARR_URL=https://your-tracearr-host \
  --env TRACEARR_API_KEY=<key> \
  -- uv run --directory /path/to/tracearr-mcp tracearr-mcp
```

## Config

| Env var | Required | Default |
|---|---|---|
| `TRACEARR_URL` | yes | - |
| `TRACEARR_API_KEY` | yes* | none (no auth header sent if unset) |

\* Every API endpoint requires auth; practically you must set it, but the
server still starts without one so errors surface from the API rather than at
startup.

## Tools

One tool per Tracearr Public API v2 endpoint. All are read-only.

| Tool | Endpoint |
|---|---|
| `tracearr_get_history` | `GET /api/v2/public/history` |
| `tracearr_get_streams` | `GET /api/v2/public/streams` |
| `tracearr_get_media` | `GET /api/v2/public/media/{ref}` |
| `tracearr_get_media_children` | `GET /api/v2/public/media/{ref}/children` |
| `tracearr_get_media_stats` | `GET /api/v2/public/media/{ref}/stats` |
| `tracearr_get_media_watchers` | `GET /api/v2/public/media/{ref}/watchers` |
| `tracearr_get_media_history` | `GET /api/v2/public/media/{ref}/history` |
| `tracearr_list_users` | `GET /api/v2/public/users` |
| `tracearr_get_user` | `GET /api/v2/public/users/{id}` |
| `tracearr_get_user_stats` | `GET /api/v2/public/users/{id}/stats` |
| `tracearr_get_user_history` | `GET /api/v2/public/users/{id}/history` |
| `tracearr_list_recently_added` | `GET /api/v2/public/recently-added` |
| `tracearr_list_libraries` | `GET /api/v2/public/libraries` |

`ref` accepts a canonical media uuid or a type-qualified provider ref such as
`movie:tmdb:584` or `show:tvdb:81189`. Cursor-paginated tools take `cursor`
and `page_size`; read `meta.nextCursor` from the response and pass it back as
`cursor` to fetch the next page. Optional params are omitted when unset so the
API's defaults apply.

## Development

```bash
make help  # list all commands
```

| Command | Does |
|---|---|
| `make sync` | `uv sync` |
| `make test` | Offline tests - one per endpoint, mocked HTTP |
| `make test-integration` | Tests against the live instance (needs `TRACEARR_URL`/`TRACEARR_API_KEY`) |
| `make build` | Build wheel + sdist into `dist/` |
| `make bump-patch` / `bump-minor` / `bump-major` | Bump the version in `pyproject.toml` + `uv.lock` |
| `make clean` | Remove build artifacts |

The release workflow (`.github/workflows/release.yml`) builds and publishes to
[Releases](https://github.com/arr-mcps/tracearr-mcp/releases) whenever a `v*`
tag is pushed - so the usual flow is `make bump-patch`, commit, then tag and
push.

The integration suite is read-only (the Tracearr public API has no write
surface), so it never modifies your instance.
