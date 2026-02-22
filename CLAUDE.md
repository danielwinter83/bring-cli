# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CLI wrapper around [miaucl/bring-api](https://github.com/miaucl/bring-api) for managing Bring! shopping lists from the terminal. Python 3.11+, async (aiohttp + bring-api).

## Development Commands

```bash
# Install in editable mode
pip install -e .

# Run directly
python -m bring_cli.main

# Run via entry point (after install)
bring <command>
```

No test suite, linter, or formatter is configured yet.

## Architecture

Single-module CLI (`bring_cli/main.py`):
- **Entry point**: `main()` → argparse → `asyncio.run(_run(args))`
- **Commands**: `lists`, `list`, `add`, `complete`, `remove` — each an `async def _cmd_*` function
- **Auth**: `BRING_EMAIL` + `BRING_PASSWORD` env vars, `BRING_LIST` for list UUID
- **Output**: plain text by default, `--json` flag for JSON output
- All Bring API interaction goes through the `bring-api` library's `Bring` class

## Key Dependencies

- `bring-api` (>=3.0.0) — async Python client for the Bring! API
- `aiohttp` (>=3.9.0) — HTTP session management
