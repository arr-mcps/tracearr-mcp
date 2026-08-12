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
The Tracearr Public API has no write surface. Every tool is read-only (`readOnlyHint=True`) — never introduce a tool that writes or deletes. Keep the whole server in `tracearr_mcp.py` unless it outgrows it.

## Tool count: this server is the one deliberate exception to the portmanteau standard
Every other server in the `arr-mcps` fleet exposes ~5-15 resource-scoped
*portmanteau* tools (an `operation` enum dispatching to per-endpoint
functions) instead of one MCP tool per REST endpoint — see the masterlist's
`AGENTS.md` for the full pattern and the rationale (hundreds of individually
registered tools blow the MCP context budget on session start). This server
is the single exception: at 13 tools it's already comfortably under the
ceiling that pattern exists to enforce, so converting it would add a
dispatch-by-string indirection layer for zero context-budget benefit. Do
**not** convert it just for consistency.

This matters beyond this one server, though: `bin/new_mcp/` scaffolds every
new MCP in this fleet from a copy of `tracearr_mcp.py`, and
`bin/new_mcp/templates.py::PLAN_PROMPT` is the brief handed to the agent that
builds out the copy. If you add new tools here (pushing this server past
~15), or if you're touching the scaffolding wizard, make sure `PLAN_PROMPT`
still explicitly instructs the portmanteau pattern for whatever gets
scaffolded — a service with a real API surface (dozens+ of endpoints) needs
the grouped-tool pattern from the start, not a bolt-on refactor later.