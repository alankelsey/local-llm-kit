---
name: ship-pr
description: Ship one PR with the local LLM doing the coding - spec, test-first split, local_iterate fix loop, verified local review, PR, CI, squash-merge. Use for any feature or fix PR in a repo that has .claude/local-llm.json (set one up with the setup-project skill).
---

# Ship a PR (Claude orchestrates, local LLM codes)

Claude's job is specs, tests-as-contract, verification and merging. The local model (`local-llm` MCP:
`local_code`, `local_iterate`, `local_review`, `local_ask`, `local_status`) writes implementation code.
The project's checks, code map roots, import aliases and conventions file come from `.claude/local-llm.json`
(missing → TypeScript defaults: `npm run -s lint|typecheck|test`, `src/`, `@/` → `src/`, `AGENTS.md`).

## 0. Environment
- `local_status`: configured model loaded, project config `present`? If no model is loaded, the first call loads it
  (~1 min). If Ollama isn't in spread mode / not running, ask the user to run `llm up` (may need sudo once).
- Switch models with `llm model <name> [ctx]`, fallback with `llm fallback <name>|off`
  (machine-wide `~/.config/local-llm/settings.json`; a project `.dev/local-llm.json` overrides it). No MCP restart needed.
- Only one model fits in VRAM at a time; the fallback (122B) is swapped in only when the default is STUCK.
- `git checkout main && git pull --ff-only && git checkout -b prN-<slug>`.

## 1. Spec (in `.tasks/prN.md`, gitignored)
- Exact exported signatures and types, data shapes, edge cases, and the design rules that apply.
- Name every file the model may write. Keep each call to <= 3 files / ~5k output tokens; split bigger work.
- List the exact import lines for each target file; the model guesses module paths badly.
- Compute expected numbers with the real formula (floating point!) or have tests compute them.
- Edits to existing files: one line per spot, anchored to an exact existing line **right next to the change**
  (the anchor check only looks a few lines around it), and pass the same anchors to `local_iterate(anchors=[...])`
  so a skipped spot fails the round:

  | # | anchor (`path: exact existing line`) | change |
  |---|---|---|
  | 1 | `src/game/events.ts: case "palletsMissing": {` | replace the case body with … |

  Anchors must be unique lines (the first match is used). The model already sees the code map (every source
  file's purpose and exports); don't repeat it in specs.
- Text you hand the model verbatim must already pass lint (e.g. JSX text with `'` needs `&apos;`).

## 2. Test-first split
- **Claude writes the contract tests** when they need bookkeeping (fake RNG queues, exact money maths,
  multi-step state). The local model is weak at that and strong at implementation.
- Simple, table-style tests can be delegated: put them in the same task as the implementation.
- Give the model fixtures/helpers to use instead of describing them in prose.
- Run the new tests once before handing off: they must fail for the right reason.

## 3. Implement
- `local_iterate(task, target_files, context_files, max_rounds=4, anchors=[...], test_filter=[...])`.
  Keep the typecheck check in `checks` even when other files are mid-change (filter tests instead).
  Imports of target files (relative and configured aliases) are added to context automatically.
- Big existing files (500+ lines): one explicitly placed edit per step. Whole-file rewrites of big files are slow
  (16k output tokens) and the default model may run out of output budget; the fallback usually recovers.
- When the model also wrote the tests, check failing expectations before letting it "fix" code: it tends to bend
  correct implementations to match its own wrong tests.
- STUCK / STILL FAILING → fallback model (3 rounds) → automatic Claude hand-off (`claude -p`, Sonnet, $1 cap,
  edits limited to `target_files`). Pass `escalate=False` when failures are expected or the problem is the environment.
- Still failing → read the errors, find the root cause, sharpen the spec and re-run (missing helper, wrong
  expectation, unclear rule, bad anchor), or make a few-line fix. Never weaken tests to get green.

## 4. Verify (Claude)
- Read the implementation diff against the spec (not every test line): spec rules, edge cases, immutability,
  determinism, layering rules from the conventions file.
- Run every configured check yourself plus the build.
- UI changes: run the app and look at it (desktop and phone widths) — screenshots, not just tests.

## 5. Review
- `git add -A`, then `local_review(base="main", focus=<spec>, context_files=[<design docs>])`.
- Only confirmed findings come back (evidence check + second-pass verifier). Still verify each one yourself;
  route real ones to `local_iterate` as a fix task.

## 6. Ship
- Commit, push, `gh pr create` with: what, how it was built (rounds, which model, what it got wrong, what Claude
  fixed), verification checklist.
- `gh pr checks <n> --watch`; on red, read `gh run view --log-failed`, fix via the loop, push.
- Green → `gh pr merge <n> --squash --delete-branch`, `git checkout main && git pull --ff-only`.
- Offload numbers live in `.llm-logs/metrics.jsonl`.

## 6b. After merging
- New recurring model mistake? Add one line to "Local model pitfalls" in the conventions file (sent with every call).

## 7. When done for the day
`llm down` (unloads the models; GPUs idle).
