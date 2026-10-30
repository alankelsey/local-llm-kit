---
name: setup-project
description: Set up a repo (new or cloned) for the Claude + local LLM workflow - checks the machine (Ollama, uv, llm command), writes .claude/local-llm.json for the repo's stack, the conventions file with local-model pitfalls, gitignore entries, the code-map header rule and the plugin settings teammates get on clone. Use when starting work in a repo that has no .claude/local-llm.json yet, or when the user asks to make a project work with the local LLM.
---

# Set up a project for local-LLM coding

Goal: after this, a fresh clone + a new Claude session can run `ship-pr` with the local model doing the coding.
Do each step, show the user what you wrote, and commit it on a branch as one setup PR.

## 1. Machine (once per machine; skip what already works)
- `command -v ollama uv gh` — all three are needed. `ollama list` shows the models; the default is
  `qwen3.8:27b` (fallback `qwen3.5:122b-a10b`). Missing model → ask before `ollama pull` (tens of GB).
- `command -v llm` — the kit's model-control script. If missing, the kit has to be cloned once and linked:
  `git clone https://github.com/alankelsey/local-llm-kit ~/projects/local-llm-kit && ln -s ~/projects/local-llm-kit/bin/llm ~/.local/bin/llm`.
  The kit folder is then `KIT=$(dirname "$(dirname "$(readlink -f "$(command -v llm)")")")`.
- `llm status` → model settings live in `~/.config/local-llm/settings.json` (machine-wide).
- `local_status` (MCP) must answer; it prints the project root and whether `.claude/local-llm.json` is present.

## 2. Project config — `.claude/local-llm.json`
Read the repo first (package.json scripts and workspaces, tsconfig paths, pyproject, Makefile, CI workflow).
Write only keys that differ from the defaults:

```json
{
  "language": "TypeScript",                      // shown to the model: "a senior engineer working in a <language> repo"
  "conventions": "AGENTS.md",                     // file sent with every call ("" = none)
  "conventions_for": [".ts", ".tsx"],             // conventions only go to tasks whose targets end with these
  "conventions_skip": ["Workflow"],               // "## " sections the model shouldn't see (Claude-only process)
  "codemap": { "roots": ["src"], "extensions": [".ts", ".tsx"], "exclude": [".test.", ".d.ts"] },
  "aliases": { "@/": "src/" },                    // import prefixes → folders, for automatic context
  "checks": { "lint": "npm run -s lint", "typecheck": "npm run -s typecheck", "test": "npm run -s test --" },
  "default_checks": ["lint", "typecheck", "test"],
  "test_check": "test"                            // test_filter paths are appended to this command
}
```
- `codemap.roots` accepts globs: a workspace monorepo uses e.g. `["packages/*/src"]`.
- Every check is a shell command run from the repo root; the test command must accept file paths appended
  at the end (`vitest run`, `pytest -q`). Lint warnings count as failures for a check named `lint`.
- Mirror tsconfig `paths` in `aliases` (`"@core/*": ["packages/sim-core/src/*"]` → `"@core/": "packages/sim-core/src/"`).
- The checks must exist. In an empty repo, create the scripts as part of the first PR instead and say so.

## 3. Conventions file
- Create or extend the conventions file (default `AGENTS.md`). Keep it short: stack, layout/layering rules,
  style rules, then `## Local model pitfalls` copied from `$KIT/templates/local-model-pitfalls.md`
  (drop items that don't fit the stack).
- Put Claude-only process (who writes what, PR steps) under `## Workflow`; that section is not sent to the model.
- If the repo also has `CLAUDE.md`, have it point at the conventions file instead of duplicating it.

## 4. Code-map header rule
Every source file in the code-map roots starts with a one-line `//` comment saying what it does (after
`"use client";` if present). The map is sent to the model with every call.
- Check locally: `python3 "$KIT/server/codemap.py" --check` (from the repo root; prints the files missing a header).
- CI step (GitHub Actions):
  ```yaml
  - run: git clone --depth 1 https://github.com/alankelsey/local-llm-kit /tmp/local-llm-kit
  - run: python3 /tmp/local-llm-kit/server/codemap.py --check
  ```

## 5. Git ignores
Add `.llm-logs/` (raw model output + metrics), `.tasks/` (PR specs) and `.dev/` (local runtime files) to `.gitignore`.

## 6. Plugin settings for the next clone — `.claude/settings.json`
Merge (don't overwrite existing keys):
```json
{
  "extraKnownMarketplaces": {
    "local-llm-kit": { "source": { "source": "github", "repo": "alankelsey/local-llm-kit" } }
  },
  "enabledPlugins": { "local-llm-kit@local-llm-kit": true }
}
```
Someone who clones the repo and trusts the folder is offered the marketplace and plugin; after install the
`local-llm` MCP server and the `ship-pr` / `setup-project` skills are there.
If the repo has its own `.mcp.json` entry named `local-llm` (an older in-repo copy), remove it and the copied tooling.

## 7. Verify
- `local_status` shows `project: <repo> (config present)`.
- `python3 "$KIT/server/codemap.py"` prints the expected files.
- Every configured check runs (`local_iterate` would run them the same way, from the repo root).
- A tiny `local_ask("Which files does the code map list?")` returns sensible output.
Then hand over to `ship-pr` for the first real PR.
