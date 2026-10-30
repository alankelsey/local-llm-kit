# local-llm-kit — conventions for code agents

## Stack
- Python 3.11+, run with `uv run --script` (inline script metadata). Runtime deps: `mcp`, `httpx` only.
- `bin/llm` is bash (`set -euo pipefail`, must pass `bash -n` and shellcheck).
- Tests: pytest, files `server/test_*.py` next to the code.

## Layout
- `server/server.py` — MCP tools and the iterate loop. Pure helpers live in `guards.py`, `codemap.py`,
  `escalation.py`, `project.py` so they can be tested without a model.
- `skills/`, `templates/`, `docs/` — Markdown for Claude; no code.

## Style
- Small named functions with type hints; module docstring on line 1 (after the uv script header).
- No new dependencies. stdlib first.
- Pure functions take explicit arguments (root, env, home) so tests can pass tmp paths; module globals
  (`ROOT`) are only read in thin wrappers.
- Every behaviour change gets a pytest contract test; tests use `tmp_path` and `monkeypatch`, never the real repo.

## Workflow
- Claude writes specs and contract tests; the local model implements (ship-pr skill).

## Local model pitfalls
- Keep imports between server modules flat (`from project import ...`); the folder is on `sys.path`, not a package.
- `str.endswith` takes a str or tuple, not a list: convert config lists with `tuple(...)`.
- Don't rewrite whole big files (server.py is ~900 lines) for small changes; use <edit> blocks.
