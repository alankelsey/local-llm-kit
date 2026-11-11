# Model workflow: code quality and lower token costs

Reviewed 2026-11-07. Documentation proposal only; no model settings, automation,
CI, or code changed. This review updates the recommendations in
[TAILSCALE-PLAN.md](TAILSCALE-PLAN.md) for the user's priorities: correctness and
maintainability first, lower total paid token cost next, speed last.

## Verdict and evidence

Keep the local 27B as the main implementer and Claude as architect, planner, and
contract-test author. Add an explicit independent review gate, normally Codex,
after PR CI. Use ordinary tools for test execution, Git operations, and CI
monitoring. OpenRouter is a provider route, not itself a model or an architect.
Claude Code and Codex are clients; record the actual model/version and reasoning
setting used in each role before comparing quality or cost.

The llm-sim pipeline document reports 220 of 272 iterate jobs passed on the 27B,
with 7 recovered by the 122B. These are historical check-pass results, not an
independent defect-rate measurement or proof that the 27B can certify its own
work. The handoff records incorrect tests, malformed edits, truncation, and a
review path that returned invalid output. These motivate tighter task contracts
and independent review more directly than extra models do.

The previous plan prioritized concurrent chat/review and replacing the 122B with
OpenRouter. Keep OpenRouter as the previously selected backup target, but make
concurrency optional. Reconsider a sequential 122B recovery path through a small
comparison before final routing is implemented: its slower speed alone is no
longer a reason to reject it. Do not silently reinstate it or assume that both
models fit in memory simultaneously.

## Role assignments

| Stage | Default owner | Cost and quality boundary |
| --- | --- | --- |
| Architecture and acceptance criteria | Claude, using a capable reasoning model validated on this repo | One design per feature; revisit only for material new evidence. Higher reasoning effort is for ambiguous or consequential design decisions. |
| Break work into steps | Same Claude planning session | Reuse the approved design; each step has one behavior, explicit interfaces, target files, and a verification command. |
| Write contract tests | Claude | Check expectations against the requirement independently of the implementation. Local drafts of simple table tests are optional and must be checked. |
| Write and repair implementation | Existing `qwen3.8:27b` via local-llm-kit | Small edits with focused context. Keep the strongest paid model out of repetitive code generation unless recovery evidence justifies it. |
| Diagnose a stuck step | Claude with the failure evidence | First classify bad spec/test, environment, edit format, truncation, or actual reasoning failure. Fix the cause before routing to another model. |
| Coding fallback | One evaluated OpenRouter model; sequential 122B is a comparison candidate | Fixed per-job allowance. Candidate slugs from llm-sim are unverified; no cheapest-model claim or permanent selection yet. |
| Run tests, build, and CI checks | pytest/Vitest, lint/typecheck, build tools, GitHub Actions | Deterministic results, no inference calls needed to execute checks or poll status. Use a model only to interpret a failure. |
| Independent PR review | Codex in a fresh review context, using a capable validated model | Give it the requirement, diff, relevant callers, tests, and check results; do not bias it with the author's assurance that the work is correct. |
| Submit PR and merge | Git/GitHub tools under the orchestrator | Preconditions are machine-checked. A model's statement that CI is green is insufficient evidence. |
| Grok or Gemini | No standing role | Optional specialist opinion or benchmark challenger only; neither is required for the complete workflow. |

The model roles are recommendations, not claims of a universal capability ranking.
No model needs a turn merely because it is available. Claude plus local code
generation and Codex review is the initial baseline. If Codex has materially
contributed implementation or test design, use a fresh independent reviewer
(normally Claude in a separate context) for that portion. Different model
families can provide diversity but do not guarantee correctness.

An OpenCode/OpenRouter orchestrator remains an experiment, not an additional
planner running beside Claude. Evaluate it as a replacement for one bounded task.
Only promote Grok, Gemini, or another candidate if controlled repository tasks
show better defect detection or lower total cost at comparable quality.

## Required sequence for each PR

1. **Architect.** Read the relevant design and code. Write user-visible behavior,
   invariants, interfaces, failure cases, and explicit exclusions. For simple
   fixes this is a short spec, not a new architecture exercise.
2. **Plan small chunks.** Aim for one coherent behavior and at most three target
   files per local call, approximately 5k output tokens as the existing skill
   recommends. Use one focused edit site for large existing files. Split by
   behavior/dependency, not arbitrary line counts. Record dependency order.
3. **Write and check tests.** Claude supplies contracts and independently checks
   fixtures/expected values. Run the tests before implementation and confirm an
   appropriate failure. Diagnose syntax, fixture, and environment failures first.
   Never weaken a correct test to accommodate implementation; when the test is
   wrong, document the requirement-based correction and review it.
4. **Implement one chunk.** The local model gets the contract, current target
   files, necessary imports/callers, and relevant conventions. One writer owns
   the worktree. Tests for later chunks stay out until their prerequisites exist.
5. **Run focused checks and repair.** Run relevant tests and typecheck where
   applicable. Give failures and a compact record of attempted fixes to the next
   round. Stop repeated identical failures for diagnosis. Re-run relevant checks
   after a fix; do not replay unchanged passing checks without a reason.
6. **Verify the assembled change.** Run all required repository checks and the
   applicable build. Inspect the diff for scope, architecture, and test quality.
   Check changed UI in the browser. Optional local review is a preliminary pass;
   invalid/empty review output is a failed review, not approval.
7. **Submit the PR.** Include the problem, resulting behavior, and verification
   evidence. Keep detailed model histories in metrics rather than a long PR body.
   Record PR number, base revision, and current head commit.
8. **Require PR CI success.** Wait for the expected checks to exist and finish
   for the current head/relevant integration commit. Missing, pending, failed,
   cancelled, or unexpectedly skipped required checks do not satisfy the gate.
9. **Review the submitted PR.** Codex reviews requirements, code, tests, boundary
   behavior, and integration assumptions after CI passes. Record the reviewed
   head/base revisions and concrete findings. An AI review artifact is not a
   substitute for any GitHub-required human approval.
10. **Iterate on findings.** Validate each finding. Add a regression test when
    appropriate, route the implementation fix to the local model, push, and run
    required CI again. Re-review the delta and affected assumptions. Any code/test
    update invalidates approval of the old head; a material base change requires
    renewed integration checks/review. Stop only when findings are resolved or
    explicitly dispositioned with evidence.
11. **Merge.** Check the final head matches the reviewed revision, required CI is
    successful, required reviews are satisfied, and no blocking discussion or
    conflict remains. Use the repo's merge policy; never bypass protections.
12. **Verify CI builds after merge.** Obtain the actual merge/squash commit on
    main and wait for its push-triggered checks and build. Confirm the build
    artifact if the workflow produces one. A green PR run or working Vite server
    is not proof of a successful main build. On failure, report the commit and
    failing job and start the normal reviewed repair/revert workflow; the task
    remains incomplete until main is healthy.

Keep review and CI evidence tied to commit IDs. CI does not prove full behavioral
correctness, and a good-looking review does not replace executable verification.

## Spend less by avoiding repeated work

- Optimize **total paid dollars and paid tokens per reviewed, successfully merged
  PR**, including failed attempts and follow-up defects. Raw token price or a
  model's first-pass test result is insufficient. Local inference has electricity
  and hardware costs but no per-token API invoice; measure those separately.
- Preserve a concise feature design and step contracts. Send relevant files,
  interfaces, tests, and errors, not the whole repository or prior chat history.
  Retrieve missing context when needed; do not omit dependencies just to hit a
  token target. Use code maps and structured tool summaries already in the kit.
- Keep large output allowance as a ceiling. Prefer smaller edits over routinely
  requesting 32k-token answers. A 256k context capacity does not require filling
  it. Keep write-step thinking off initially as planned; evaluate reasoning for
  architecture, root-cause diagnosis, and review separately.
- Start with at most two corrective local attempts per chunk, then diagnose if
  they fail; allow another attempt only for a materially improved hypothesis.
  This is a proposed routing policy, not a change to the current four-round
  default. The same cap must span reworded submissions of one failed step.
- On a genuine model limitation, choose one budgeted recovery tier. Do not always
  pay both OpenRouter and a Claude coding handoff. A final Claude handoff requires
  explicit remaining job budget and evidence it is useful. At budget exhaustion,
  preserve the task state and report it blocked on budget; do not merge or lower
  verification standards to finish.
- Reserve review capacity before spending on optional second opinions or an
  orchestrator experiment. Do not launch every model as a reviewer. Batch related
  issues into one focused repair pass, then review the resulting delta.
- Keep $5/day as the existing **OpenRouter** ceiling, not a claim of a total
  system ceiling. Track direct Anthropic/OpenAI/xAI/Google API spend separately,
  and track subscription usage/limits separately from cash. Define overall and
  per-PR paid budgets before unattended paid operation; do not invent limits or
  assume subscriptions make API calls free.
- All enabled paid clients must honor their allocations. Reserve a conservative
  request-cost bound atomically before dispatch and reconcile actual usage after
  it returns. Retain unresolved reservations after timeouts until reconciled;
  avoid blind duplicate retries. Use America/Boise as the proposed daily reset
  timezone. A local ledger cannot enforce calls from a client that bypasses it.

## Gaps found in current automation

Reviewed files on 2026-11-07; these remain unchanged:

- `skills/ship-pr/SKILL.md` reviews locally before creating a PR, then allows
  green CI to lead directly to merge. It lacks the required review gate for the
  submitted PR and explicit verification of main's post-merge CI.
- `llm-sim/.tasks/tools/ship.sh` similarly merges after checks without a review
  gate, then restarts Vite. That restart does not verify main CI. It also binds
  Vite to `0.0.0.0`, conflicting with the proposed loopback/private-preview setup.
  Do not treat this script as implementing the reviewed workflow.
- llm-sim's CI already runs on PRs and main pushes and includes lint, typecheck,
  tests, code-map check, and build. Add a reliable waiter/gate, not a duplicate
  build workflow. Its code-map step clones the latest kit; pinning a tested kit
  revision is a separate reproducibility improvement to consider.
- The kit's CI runs pytest and `bash -n`; it lacks the shellcheck required by
  AGENTS.md. Add that in a later implementation PR. The kit has no application
  bundle build; post-merge success means its applicable checks, while llm-sim
  must also produce a successful application build.
- Per-role routing, shared budget reservations, independent review enforcement,
  durable job state, and concurrency are planned features, not deployed guarantees.

## Evaluation and implementation order

First make the lifecycle gates reliable and use small contracts with the existing
local model. Add job identity/reconnect safeguards. Then implement provider routing
and budget enforcement before any paid fallback trial. Concurrency and additional
model roles come later only if needed; quality gates and cost control take priority.

Evaluate a fixed small set of historical ordinary tasks and failures, including
bad fixtures, multi-file integration, truncation, and subtle regression cases.
Reset isolated worktrees to the same starting commits and use the same contracts
and budgets. Keep additional acceptance tests hidden from candidate implementers.
For reviewers, include known defects and clean changes to measure both missed
bugs and false positives. Compare local-only, sequential local recovery, and
OpenRouter recovery; evaluate alternative orchestrators separately.

Record actual model/version/provider, configuration, input/output/cached/reasoning
tokens where available, paid cost, repair rounds, accepted defects found, missed
defects, review completion, and main-build success. Select the cheapest workflow
that meets the quality bar; use elapsed time only as a secondary operational metric.
The old candidate model names remain candidates until current catalog/pricing and
repository evidence justify them. No benchmarks or paid calls ran for this review.

## Local engine trial: radiance

Added 2026-11-10. Proposal only; nothing installed or changed.
[radiance](https://codeberg.org/StillDeadcode/radiance) is an Apache-2.0 C++/HIP
inference server for AMD GPUs. Its bundled kernels target RDNA4, and its serve
flags are written for two 32 GB Radeon AI PRO R9700 cards, which is this machine.
It supports tensor parallelism across both cards (`--tp`) and speculative decoding
with a bundled drafter, and it lists Qwen3.8 models. Its README reports 103–141
tok/s for Gemma 4 31B on two R9700s. qwen3.8:27b runs at about 53 tok/s on
Ollama 0.40.6 today. These figures are self-reported and unverified. The project
is small: 96 stars and 930 commits, with v1.17 releases in November 2026.

The trial must not replace Ollama until it meets the same quality bar as any
other route. Speed is secondary, as in the rest of this plan.

Gaps before it could be used:

- **No Ollama API.** It speaks the OpenAI chat/completions/Responses, Anthropic
  Messages, and llama-server APIs. The kit calls Ollama's `/api/chat` with a
  per-call `num_ctx`, `num_predict` and JSON-schema `format`, and `llm status` /
  `llm model` / `llm fallback` read and swap Ollama models. An OpenAI-compatible
  backend in the kit would be needed. That is the same adapter the OpenRouter
  route needs, so build it once.
- **Structured output is unconfirmed.** Reviews and verification depend on a JSON
  schema. Confirm radiance enforces one (or that a prompt-only JSON contract is
  reliable) before routing reviews to it.
- **Model format.** Models must be converted to `.rad` containers with
  `rad-convert` from Hugging Face checkpoints. Confirm a recipe for the exact
  qwen3.8 27B variant, at a quantization comparable to the Ollama tag in use.
- **Memory.** Ollama and radiance share the two cards. Run only one with a loaded
  model at a time.

Steps, stopping at the first failure:

1. Run its Docker image alongside Ollama with Ollama's models unloaded. Convert
   qwen3.8 27B. Record the image version, quantization, `--tp` setting, and
   whether speculative decoding is on.
2. Smoke test: decode tok/s at a long context (more than 100k tokens of input), a
   32k output limit, and a JSON-schema response.
3. Add an OpenAI-compatible backend option to the kit behind a setting, with
   Ollama still the default.
4. Replay the fixed historical task set from the evaluation section on both
   engines, with the same contracts, budgets, and starting commits. Compare pass
   rate, repair rounds, review completion, and accepted and missed defects. Record
   elapsed time last.
5. Adopt it only if the pass rate and review quality are equal or better.
   Otherwise record the result in [TOOLING.md](TOOLING.md) and remove it.

## Sources

- [LLM Sim pipeline decisions](../../llm-sim/docs/openrouter-pipeline-plan.md)
- [Existing ship-pr workflow](../skills/ship-pr/SKILL.md)
- [Local benchmark history](TOOLING.md)
- [radiance README](https://codeberg.org/StillDeadcode/radiance): AMD/HIP inference
  server; hardware, API, and benchmark claims above are from its README (2026-11-10).
- [LLM Sim handoff](../../llm-sim/.tasks/HANDOFF.md)
- [Codex code review](https://learn.chatgpt.com/docs/code-review): supports local
  checkout review and PR review routes; use a fresh review context for this plan.
- [Anthropic workflow guidance](https://www.anthropic.com/research/building-effective-agents):
  supports starting with simple workflows and evaluating added complexity.
- [OpenRouter usage accounting](https://openrouter.ai/docs/cookbook/administration/usage-accounting):
  provides usage/cost data; implementation must verify the schema for its chosen
  API endpoint rather than assuming every endpoint has the same fields.
