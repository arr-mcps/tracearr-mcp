# AGENTS.md — tracearr-mcp

MCP server exposing Tracearr's Public API v2 (REST, read-only) as tools so an LLM can query Plex, Jellyfin, and Emby monitoring data: watch history, active streams, media, users, libraries, and recently added items. Uses FastMCP, `uv` for deps.

## Testing
- Offline suite: `make test` (or `uv run pytest`)
- Live integration (needs `TRACEARR_URL`/`TRACEARR_API_KEY`): `make test-integration`

## Release workflow
Always use the `make bump-*` targets to bump the version (`uv version --bump patch|minor|major`), which updates `pyproject.toml` and `uv.lock` together. Do NOT edit the version by hand.

- Bump: `make bump-patch` (or `bump-minor` / `bump-major`)
- Commit message is **just the version**, e.g. `0.1.2` — nothing else.
- Tag it `v<version>` (e.g. `v0.1.2`).
- Push main and the tag:
  ```
  git push origin main
  git push origin v<version>
  ```
- Deploy to the Proxmox host (root SSH key): pull the repo then reinstall the uv tool:
  ```
  ssh root@192.168.50.3 -- 'cd /root/tracearr-mcp && git fetch origin && git reset --hard origin/main'
  ssh root@192.168.50.3 -- 'cd /root/tracearr-mcp && uv tool install --force .'
  ```
  The host runs it via `uv tool install` → `/root/.local/bin/tracearr-mcp` (not from the repo). There is no `/home/savagecore/Documents/christopfarr/mcp/tracearr-mcp` copy.

## Read-only note
The Tracearr Public API has no write surface. Every tool is read-only (`readOnlyHint=True`) — never introduce a tool that writes or deletes. Keep the whole server in `tracearr_mcp.py` unless it outgrows it; add tools one per endpoint with the `tracearr_` prefix. Base path `/api/v2/public` is hardcoded in `build_client`.