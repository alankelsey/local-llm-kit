# Tailscale implementation plan

Prepared 2026-11-07 for local-llm-kit. Status: planned; no networking, accounts,
services, or provider configuration changed.

Priority update: code quality and lower token costs matter more than speed.
[MODEL-WORKFLOW-PLAN.md](MODEL-WORKFLOW-PLAN.md) contains the reviewed model roles,
cost controls, and required lifecycle through independent PR review, merge, and
successful CI on main. Its recommendations supersede earlier speed/concurrency
assumptions below. Grok and Gemini have no mandatory role.

Revised after reading llm-sim's `docs/openrouter-pipeline-plan.md`,
`docs/INDEX.md`, the AI decision-maker section of `docs/plan.md`, and the latest
section and operational lessons in `.tasks/HANDOFF.md`. Those documents describe
planned pipeline behavior, not evidence that it has been implemented.

## Source and assumptions

Source: the owner's Google Doc "tailscale" in Drive / LocalAi. A text copy is kept there as "tailscale connect",
not in this repo.

Assume the existing Ubuntu GPU machine remains the execution host, with Android
and a laptop as clients. Confirm actual hostnames, Linux username, tailnet identity,
installed clients, and desired provider billing before implementation. Treat Grok
as the xAI API unless an existing Grok terminal client is identified.

The source suggests Tailscale, Shellular, and Cloudflare. Use Tailscale for this
plan. Correct two details: a node joins a private tailnet, not automatically the
whole home LAN; peer connections can use encrypted relays when direct connectivity
is unavailable. Use the official Linux install instructions, rather than the
source's unverified `curl https://tailscale.com | sh` command.

## Target design

```text
Android / laptop
    | Tailscale encrypted connection
    v
Ubuntu host: SSH -> tmux -> project working directory
                           | Claude Code + existing local-llm MCP
                           | Codex CLI
                           | selected Grok / OpenRouter API client
                           v
                    Ollama on 127.0.0.1:11434

Ubuntu -> normal outbound HTTPS -> Anthropic / OpenAI / xAI / OpenRouter
Optional later: tailnet HTTPS Serve -> loopback Ollama or authenticated web UI
```

### Pipeline requirements from LLM Sim

The newer pipeline decisions supersede the initial plan's treatment of OpenRouter
as just an independent terminal client:

```text
Claude Code architect/planner/test author (alternative orchestrator is a trial)
    -> project-local stdio MCP -> local_iterate -> qwen3.8:27b coder
                                      | failure -> diagnose spec/tests/tooling
                                      | genuine limitation -> budgeted recovery
    -> local_ask / local_review -> optional preliminary local pass
    -> PR + green CI -> independent Codex review -> fixes + CI + re-review
    -> merge -> verify main CI/build

OpenRouter is the planned cloud recovery route; a sequential 122B comparison
is proposed for cost savings. Grok/Gemini remain optional comparison candidates.
```

- The earlier decided target replaces the 122B fallback with OpenRouter. With
  quality and cost now ahead of speed, compare a sequential local recovery path
  before finalizing that tradeoff. No configured model changes in this review.
- Coder target: 256k context; output limit 16,384 -> 32,768, with thinking off for
  writes. Chat/review uses another slot of the same model, or a separate 27B at
  64k if sharing is too slow. GPU-memory figures in the source are estimates;
  benchmark concurrent context memory and latency if concurrency is later needed.
  Start sequentially; a second resident model is not a quality requirement.
- Optional kit concurrency may allow ask/review beside iterate later. Tailscale
  cannot remove server serialization or GPU contention. Independent final review
  examines a stable PR revision, not files being edited by a live coder.
- `OPENROUTER_API_KEY` comes from the host environment only, never settings,
  prompts, logs, or metrics. The daily OpenRouter cap is **$5 total**, including
  the planned orchestrator trial's allocation (example: $3 orchestrator/$2 backup).
- Every MCP process/client must participate in one shared budget mechanism.
  Concurrent read-then-sum checks can overspend: require atomic reservations,
  settlement against actual cost, and a defined daily reset timezone. An external
  OpenCode client needs a compatible enforced allocation or provider-side limit;
  kit-only metrics cannot enforce spending by that independent client. Unknown
  prices or an unavailable budget ledger must fail closed for paid requests.
- OpenRouter model names in the source are candidates, not verified deployment
  selections. Verify exact slugs, availability, pricing, and output limits during
  the planned capped bake-off; do not choose them as part of networking setup.

All orchestrators, budget state, project files, and MCP processes should initially
remain on Ubuntu. Phone/laptop access is a control connection; no remote MCP
HTTP listener or separate public port per model is required. If laptop-local
orchestration is introduced later, explicitly design project ownership, shared
budget accounting, and authenticated MCP transport first.

The asset pipeline is production-time work: generation -> review -> ordinary
files -> game integration. It needs outbound provider access and optionally a
private preview, not inbound provider access to Ollama. Whether image generation
shares the $5 cap remains undecided in the source; disable paid image runs until
that allocation is set. Keep this separate from the game's future runtime
`DecisionProvider`, whose timeout/invalid-response fallback is scripted Game AI.

Tailscale protects access to the host. Provider authentication and billing remain
separate. Cloud prompts still go to the selected provider; using Tailscale does
not make cloud inference local. No exit node or subnet router is needed.

## 1. Inventory and establish private access

1. Record Ubuntu version, Tailscale version, current listeners/firewall rules,
   Ollama bind address, current SSH access, and installed AI clients. Back up any
   tailnet policy or service configuration before changing it.
2. Install Tailscale from its official Ubuntu instructions and the Android app.
   Enroll the host and clients in the intended tailnet; secure the identity account
   with MFA. Choose a stable hostname, such as `llm-host`.
3. Enable MagicDNS as needed. Verify `tailscale status` and
   `tailscale ping llm-host` from a client. Test the phone over cellular data.
4. Define explicit tailnet grants for the intended owner/client devices to the
   host's TCP 22 only. Review existing broad allow rules: adding a narrow grant
   does not cancel another broad grant. Use policy tests for allowed and denied
   identities. If device-specific restrictions are required, use verified device
   selectors/posture rules rather than assuming a user grant restricts devices.
5. Use Tailscale SSH on Ubuntu with a separate SSH policy permitting only the
   intended non-root Linux account and appropriate identity rechecks. Validate
   the policy before enabling `sudo tailscale set --ssh`. Ordinary key-based
   OpenSSH over the tailnet is an alternative; it uses sshd's own authentication.
6. Keep an existing console/recovery path while testing. Confirm TCP 22 is not
   reachable through an unintended public or LAN listener under the chosen firewall
   policy. Do not add router forwarding or enable Funnel.

Acceptance: the authorized phone/laptop can SSH over cellular/another network;
an unauthorized tailnet identity cannot. Existing local access still works.

## 2. Run tools on Ubuntu through persistent sessions

Install/use tmux as a host utility, with separate sessions per tool or task:

```sh
ssh alan@llm-host                 # replace user and hostname with verified values
tmux new-session -A -s local-ai
cd ~/projects/local-llm-kit
```

Reconnect to the same session after phone sleep or network interruption. Keep
separate worktrees for concurrent agents that edit the same repository. tmux
survives a disconnected SSH client, but not a host reboot without added recovery.

The llm-sim handoff reports that a timed-out `local_iterate` can continue writing
after the caller disconnects. A phone disconnect or timeout must not trigger an
automatic resubmission, branch switch, model unload, or fallback replay. Inspect
the original job's process, logs, and working tree before resuming. Plan durable
job IDs/status and explicit cancellation before unattended remote operation;
tmux alone does not supply those guarantees. Ask/review may run alongside coding,
but only one writer owns a worktree, and tests for a later step must wait until
the earlier writer finishes.

| Tool | Initial integration | Acceptance check |
| --- | --- | --- |
| Local LLM | Keep Ollama loopback-only; run existing CLI/MCP on Ubuntu | `uv run --script server/cli.py status`, then a small ask |
| Claude | Run Claude Code on Ubuntu with its own supported login; retain existing plugin | Confirm `local_status` and a read-only local-model request |
| Codex | Run Codex CLI on Ubuntu as the default independent PR reviewer | Supported login and a review tied to a stable PR revision |
| Grok / Gemini | Optional clients for a specific comparison or unresolved question | No deployment or call required for the baseline workflow |
| OpenRouter | Planned budgeted coding backup; alternative orchestrator is a later experiment | Shared-cap enforcement and one capped request per enabled route |

Do not assume the Grok consumer subscription includes API access. Verify each
provider's access and costs independently. Set low provider spending limits where
available; keep credentials in the user's protected host credential/config store,
outside git and prompt logs. Never copy keys into this document.

The current `.mcp.json` starts a stdio server with Claude plugin substitutions.
That is not a network MCP endpoint or a ready-made Codex configuration. If local
tools are needed inside Codex, register an equivalent stdio MCP command using
absolute paths and an explicit `REPO_ROOT`, then verify the installed Codex
version's configuration format. This can remain entirely on the Ubuntu host.

## 3. Optional direct model or browser access

Only add this if clients need inference without an SSH session. Keep Ollama bound
to loopback and use Tailscale Serve to proxy it privately over HTTPS. Inspect
existing Serve configuration first, choose the listener, and permit TCP 443 only
for intended clients. Consult the installed version's `tailscale serve --help`;
the usual single-service setup is `tailscale serve --bg http://127.0.0.1:11434`.

Verify the actual generated HTTPS URL from `tailscale serve status`. Test
`/api/tags`, generation, streaming, timeouts, and disconnect behavior. Ollama access
also exposes administrative API capabilities: authorize only fully trusted
clients, or add an authenticated, restricted gateway before broader use.

The kit reads `OLLAMA_URL` in both `server/server.py` and `bin/llm`; a client-side
MCP process can use the verified HTTPS URL. However, its file edits and checks run
on that client's filesystem. `bin/llm` also performs local systemd/GPU operations;
setting `OLLAMA_URL` does not make those operations remote. Run management commands
on Ubuntu over SSH. Do not simply set `OLLAMA_HOST=0.0.0.0`.

A browser UI is a separate optional project: bind it to loopback, require login,
store provider secrets server-side, and publish through a separately planned
Serve listener. Tailscale alone does not supply a unified chat interface. Cloud
Claude/Codex/Grok web sessions do not automatically join this tailnet; use the
host-based tools for private-resource access in this design.

## 4. Repository implementation work, if requested

The SSH-first deployment needs no Python runtime changes or new runtime deps.
Follow the repository workflow for any later code work: Claude writes specs and
pytest contracts; the local model implements; Claude verifies.

Proposed small, separately reviewable changes:

1. Add an operational Tailscale runbook and link it from README, using verified
   machine values and recording recovery steps.
2. If remote inference is used, specify contracts for environment-selected
   `OLLAMA_URL`, unchanged localhost default, unreachable endpoint diagnostics,
   and request URL construction. Use mocked httpx and tmp paths, not live models.
3. If extending `bin/llm`, specify that remote inference mode cannot silently run
   local machine management. Add contract tests before implementation and run
   `bash -n` plus shellcheck.
4. Keep xAI/OpenRouter provider support separate from Tailscale. The current kit
   speaks Ollama; swapping a URL will not implement cloud provider protocols.
   Specify explicit provider/model selection, opt-in cloud transmission, key
   redaction, request limits, and mocked error/streaming tests before adding an
   adapter using existing httpx. The approved target includes automatic
   OpenRouter backup once configured and budgeted; Grok automatic fallback has
   not been specified. Before provider rollout, add contracts for concurrent
   budget reservations, capped/unknown-cost skips, credential redaction, tier
   ordering, parallel ask/review, and disconnects without duplicate submissions.

Implementation sequence: establish private SSH first; implement the review,
merge, and main-CI gates plus job identity/reconnect safeguards; add provider
routing and budget enforcement; run the capped recovery comparison. Alternative
orchestrators, concurrency, private previews, and the asset experiment follow
only as needed. Keep networking independent of unimplemented pipeline features.

## Completion and recovery

Complete the initial rollout when SSH, reconnecting tmux, local inference, Claude,
and Codex review pass from the remote workflow. Validate OpenRouter when its
budgeted integration is implemented; Grok/Gemini are optional. Verify public
access remains closed, credentials stay out of git/logs,
and owner device revocation removes private access. Repeat connectivity checks
after an Ubuntu reboot. Optional HTTPS/model/UI work has its own acceptance gate.

For the later pipeline rollout, demonstrate independent review of a stable PR,
successful CI after merge, budget exhaustion without a paid call, two callers
competing for the last budget allocation, and a disconnect/reconnect without
duplicate writes or spend. Test concurrent preliminary review only if enabled.
Keep existing Vite servers loopback-only; if a phone preview is wanted, use a
distinct private Serve listener for the verified worktree's dev server. The
handoff mentions :5173 for the user's main preview and :5174 for agent checks;
inspect live listeners before choosing either, and verify Vite host/HMR settings
for the actual tailnet URL instead of allowing all hosts.

Rollback: stop only the new Serve listener, disable Tailscale SSH if enabled,
restore the saved policy/firewall/service settings, remove new client endpoint
overrides, and revoke unused device registrations. Preserve the verified console
or prior SSH recovery route until rollback has been tested. Rotate any exposed
provider credential independently of Tailscale device removal.

## Official references

Local pipeline sources (reviewed without modifying llm-sim):

- [Pipeline decisions](../../llm-sim/docs/openrouter-pipeline-plan.md)
- [Design index](../../llm-sim/docs/INDEX.md)
- [Game runtime AI design](../../llm-sim/docs/plan.md)
- [Handoff and disconnect lessons](../../llm-sim/.tasks/HANDOFF.md)

- [Tailscale Linux installation](https://tailscale.com/download/linux)
- [Tailscale SSH and policy](https://tailscale.com/docs/features/tailscale-ssh)
- [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve)
- [Ollama networking FAQ](https://docs.ollama.com/faq)
- [Claude Code overview](https://code.claude.com/docs/en/overview)
- [Codex authentication](https://learn.chatgpt.com/docs/auth?surface=cli)
- [xAI API quickstart](https://docs.x.ai/developers/quickstart)
- [OpenRouter authentication](https://openrouter.ai/docs/api_reference/authentication)
