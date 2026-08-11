# AGENTS.md

Conventions for working in this repository. Follow these when making changes.

## Project

`tracearr-mcp` — a single-file Python MCP server that exposes [Tracearr](https://docs.tracearr.com/api)'s Public API v2 (REST, read-only) as MCP tools. Built on [FastMCP](https://gofastmcp.com), ported from the `dashy-mcp` template.

Layout:

- `tracearr_mcp.py` — all MCP tools + client. One tool per API endpoint (13 total), all `readOnlyHint=True`. Base path `/api/v2/public` is hardcoded in `build_client`.
- `tests/test_tools.py` — offline suite (mock HTTP via `httpx.MockTransport`); no network.
- `tests/test_live.py` — integration suite against a real instance; gated on `TRACEARR_URL`/`TRACEARR_API_KEY`.
- `pyproject.toml` — package metadata, script entrypoint `tracearr-mcp`.
- `Makefile` — command wrappers.
- `.github/workflows/release.yml` — publishes a GitHub Release on a `v*` tag push.

## Commands

Use these to verify work (mirrored in the `Makefile`):

```bash
make sync          # uv sync (install dependencies)
make test          # offline test suite (uv run pytest)
make test-integration  # tests against a live Tracearr (needs TRACEARR_URL/TRACEARR_API_KEY)
make build         # build wheel + sdist into dist/
```

Lint/typecheck: none configured for this project. `pytest` is the only gate — always run `make test` after changes.

## Release / versioning

- Version lives in `pyproject.toml`. Current: `0.0.0`.
- Bump with `make bump-patch` / `bump-minor` / `bump-major` (`uv version --bump ...`), which also updates `uv.lock`.
- Flow: bump, commit, then `git tag v0.0.x && git push --tags`. The release workflow builds and publishes automatically.

## Repository conventions

- Default branch: `main`.
- License: MIT, `Copyright (c) 2026 SavageCore`.
- Mirror upstream conventions from `dashy-mcp` where possible (Makefile, dependabot, release workflow, test patterns).
- All API tools are read-only — never introduce a tool that writes or deletes (the Tracearr public API has no write surface).
- Keep the whole server in `tracearr_mcp.py` unless the module outgrows it; add tools one per endpoint with the `tracearr_` prefix.
