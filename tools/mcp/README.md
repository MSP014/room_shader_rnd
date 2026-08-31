# Omniverse MCP Helpers

Project-level helpers for Room Map Shader RnD research. They query local NVIDIA
Omniverse MCP servers for OpenUSD, Kit, and OmniUI reference material while the
Houdini/VEX-to-MDL parallax-interior workflow is being developed.

This is a lightweight development/reference tool, not a runtime dependency.

## Requirements

- Docker Desktop running.
- Local MCP servers as needed:
  - USD Code MCP: `localhost:9903`;
  - Kit MCP: `localhost:9902`;
  - OmniUI MCP: `localhost:9901`.
- Python 3.12 through the `shader_rnd` Conda environment.
- `KIT_USD_AGENTS_ROOT` pointing to a local clone of
  `NVIDIA-Omniverse/kit-usd-agents`.
- Required credentials configured locally for `kit-usd-agents`.

## Start servers

```powershell
Push-Location "$env:KIT_USD_AGENTS_ROOT\source\mcp"
docker compose --env-file .env -f docker-compose.ngc.yaml up -d usd-code-mcp kit-mcp omni-ui-mcp
Pop-Location
```

Use the matching `docker compose ... stop` command to stop the services.

## Usage

```powershell
conda run -n shader_rnd python tools/mcp/usd_mcp_client.py list-tools
conda run -n shader_rnd python tools/mcp/kit_mcp_client.py search-knowledge "Kit extension lifecycle"
conda run -n shader_rnd python tools/mcp/omni_ui_mcp_client.py class-detail "Button"
```

Each helper accepts `--url` to override its local endpoint.

## Repository boundary

Keep only these neutral helper scripts and this documentation in the repository.
Never commit local `.env` files, credentials, `kit-usd-agents` clones, Docker
volumes/images, build output, caches, or generated MCP artefacts.
