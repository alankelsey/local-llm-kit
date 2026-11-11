# Remote access from a phone

Runbook for watching and driving terminal agents (Grok, Claude Code, the kit's `llm` command) on the GPU host from a
phone. Set up and checked on 2026-11-11. The design and its later stages are in [TAILSCALE-PLAN.md](TAILSCALE-PLAN.md).

```text
phone (Tailscale app + SSH app)
    | Tailscale, encrypted; no open router port, no public listener
    v
llm-host: Tailscale SSH -> tmux session -> grok / claude / llm
```

## What is in place

- Tailscale on the host and the phone, signed in to the same tailnet. Host name `llm-host`.
- **Tailscale SSH** (`tailscale up --ssh`). There is no OpenSSH server on the host, so port 22 answers only on the
  tailnet. Login is the Tailscale identity: no password, no key. The default tailnet policy lets the owner reach their
  own devices as a non-root user, with a browser re-check.
- tmux, so a session survives the phone sleeping or losing signal.

## Host setup (once, needs sudo)

```sh
sudo apt install -y tmux
curl -fsSL https://tailscale.com/install.sh | sh   # official installer
sudo tailscale up --ssh --hostname llm-host        # opens a login URL; use an account with MFA
tailscale status                                   # host and phone both listed
```

## Phone setup (once)

1. Install the Tailscale app and sign in to the same account. Leave it connected.
2. Install an SSH client (Termius or JuiceSSH on Android).
3. New host: `llm-host` (or its `100.x` address from `tailscale status`), port 22, user = the host's Linux user,
   password and key left blank.
4. Connect. The first time, Tailscale may print a link to approve the login; open it on the phone.
5. Test once on mobile data, not only home Wi-Fi.

If the client asks for a password, the connection is not going through Tailscale (app off, or a LAN address was used).

## Daily use

```sh
tmux new -A -s grok -c ~/projects/llm-sim grok      # start Grok, or attach if it is already running
tmux new -A -s claude -c ~/projects/llm-sim claude  # same for Claude Code
tmux ls                                             # what is running
```

tmux keys (press `Ctrl-b`, release, then the key): `d` detach and leave it running, `[` scroll back (`q` to leave),
`s` switch session. Most phone SSH apps have a Ctrl key on an extra-keys row.

Claude Code also has `/remote-control`, which needs none of this. Grok has no phone mode of its own, so tmux is the
route for it.

## Safety notes

- Check the agent's approval mode before driving it from a small screen. A Grok session started with
  `--always-approve` runs every command and edit without asking.
- A dropped connection must not trigger a resubmit. Reattach and look at the running job first (see the disconnect
  notes in [TAILSCALE-PLAN.md](TAILSCALE-PLAN.md#2-run-tools-on-ubuntu-through-persistent-sessions)).
- Dev servers bound to `0.0.0.0` (Vite, ad hoc Python servers) are reachable on the LAN whatever Tailscale does.
  Bind them to `127.0.0.1` and use a private Tailscale Serve listener if a phone preview is wanted.
- Do not enable Funnel or forward a router port.

## Undo

```sh
sudo tailscale set --ssh=false   # turn off Tailscale SSH
sudo tailscale down              # leave the tailnet
```

Remove the phone or host from the Tailscale admin console to revoke it.
