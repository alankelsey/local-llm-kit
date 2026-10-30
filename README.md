# local-llm-kit

A Claude Code plugin for one workflow: **Claude plans and verifies, a local model writes the code.**
Claude writes the spec and the contract tests. A local Ollama model writes the implementation and fixes it until
the project's checks pass. Claude then reviews, verifies and ships. If the local model gets stuck, a bigger local
model takes over, and after that a capped Claude hand-off.

## What's in it
| Part | What it does |
|---|---|
| `local-llm` MCP server (`server/`) | `local_code`, `local_iterate` (write → check → fix loop with anchors, fallback model, Claude hand-off), `local_review` (evidence-checked findings), `local_ask`, `local_status` |
| `ship-pr` skill | One PR end to end: spec → contract tests → `local_iterate` → verify → `local_review` → PR → CI → merge |
| `setup-project` skill | Makes a repo ready: `.claude/local-llm.json`, conventions + pitfalls, code-map rule, gitignore, plugin settings |
| `bin/llm` | Machine side: `llm up / status / down / model M [ctx] / fallback M|off / restore` |
| `templates/` | Local-model pitfalls to copy into a project's conventions file |

## Machine setup (once)
```sh
# needs: ollama, uv, gh, git, python3
git clone https://github.com/alankelsey/local-llm-kit ~/projects/local-llm-kit
ln -s ~/projects/local-llm-kit/bin/llm ~/.local/bin/llm
ollama pull qwen3.8:27b            # default coder (~29 GB with a 256k context)
ollama pull qwen3.5:122b-a10b      # optional fallback (~56 GB); `llm fallback off` to skip
llm up                             # spread Ollama over the GPUs (sudo once) and preload the model
claude plugin marketplace add alankelsey/local-llm-kit
claude plugin install local-llm-kit@local-llm-kit
```
Model settings are machine-wide in `~/.config/local-llm/settings.json` (`llm model …` writes it).
A project's own `.dev/local-llm.json` overrides them, and `LOCAL_LLM_SETTINGS` overrides both.

## Project setup
In the repo, open Claude Code and say "set this project up for the local LLM" (the `setup-project` skill).
It commits `.claude/settings.json` with the marketplace and plugin enabled, so **the next clone just works**:
clone → `claude` → trust the folder → accept the plugin → `ship-pr`.

Per-project config is `.claude/local-llm.json`. Missing keys fall back to the TypeScript/npm defaults in
`server/project.py`:

```json
{
  "language": "TypeScript",
  "conventions": "AGENTS.md",
  "conventions_for": [".ts", ".tsx"],
  "conventions_skip": ["Workflow"],
  "codemap": { "roots": ["src"], "extensions": [".ts", ".tsx"], "exclude": [".test.", ".d.ts"] },
  "aliases": { "@/": "src/" },
  "checks": { "lint": "npm run -s lint", "typecheck": "npm run -s typecheck", "test": "npm run -s test --" },
  "default_checks": ["lint", "typecheck", "test"],
  "test_check": "test"
}
```

## Shell use
`uv run --script server/cli.py {status|code|iterate|fix|review|ask}` from inside a project
(`REPO_ROOT` overrides the git top level). Logs and metrics go to `<project>/.llm-logs/`.

## Developing the kit
`uv run --with pytest --with 'mcp>=1.9,<2' --with httpx pytest -q server`. The kit is configured for itself
(`.claude/local-llm.json`, `AGENTS.md`), so the plugin can work on its own code. History, benchmarks and the
backlog are in `docs/TOOLING.md` (the kit started in [ai-wars](https://github.com/alankelsey/ai-wars)).
