# BSGateway Worker

Self-hosted worker agent that runs Claude Code or Codex CLI tasks dispatched
from a BSGateway instance.

## Install (one-liner)

On the machine where you want to run tasks:

```bash
# Prereqs: Python 3.11+ and at least one of:
#   npm install -g @anthropic-ai/claude-code
#   npm install -g @openai/codex

curl -fsSL http://<gateway-origin>/api/v1/workers/install.sh | bash
```

This downloads the worker source to `~/.bsgateway-worker`, installs
dependencies via `uv` (or `pip`), and creates a launcher at
`~/.bsgateway-worker/bsgateway-worker`.

## Run

The first run registers the worker with the gateway using an install token.
Mint one in the gateway UI (**Models → Install Worker → Generate Token**),
then:

```bash
BSGATEWAY_INSTALL_TOKEN=<paste-install-token> \
  ~/.bsgateway-worker/bsgateway-worker
```

After registration the worker's persistent token is saved to
`~/.bsgateway-worker/.env`, so subsequent runs need no arguments:

```bash
~/.bsgateway-worker/bsgateway-worker
```

## How it works

1. **Register**: `POST /api/v1/workers/register` with `X-Install-Token`.
   Server resolves the install token to a tenant, creates both a `workers`
   row and a matching `tenant_models` row (pinned via
   `extra_params.worker_id`), and returns a one-time worker token.
2. **Heartbeat**: every loop iteration, `POST /api/v1/workers/heartbeat`
   keeps the worker's `status='online'`.
3. **Poll**: `POST /api/v1/workers/poll` reads from Redis Stream
   `tasks:worker:{worker_id}` (consumer group per worker).
4. **Execute**: runs the CLI (`claude --print` or `codex --quiet --full-auto`)
   inside `context.workspace_dir`, capturing stdout/stderr.
5. **Report**: `POST /api/v1/workers/result` writes the result back to
   `executor_tasks.output` / `.error_message` and marks it `done`/`failed`.

## Configuration

All settings use the `BSGATEWAY_` environment prefix, loaded from
`~/.bsgateway-worker/.env` automatically:

| Variable | Default | Purpose |
|----------|---------|---------|
| `BSGATEWAY_SERVER_URL` | `http://localhost:8000` | Gateway origin (auto-injected during install) |
| `BSGATEWAY_INSTALL_TOKEN` | _(required first run)_ | Mint via gateway UI |
| `BSGATEWAY_WORKER_TOKEN` | _(auto-set)_ | Persistent token after registration |
| `BSGATEWAY_WORKER_NAME` | hostname | Also becomes the tenant model name |
| `BSGATEWAY_POLL_INTERVAL_SECONDS` | `5` | Between polls when queue is empty |
| `BSGATEWAY_MAX_PARALLEL_TASKS` | `5` | Concurrent CLI executions |
| `BSGATEWAY_SKIP_PERMISSIONS` | `true` | Pass `--dangerously-skip-permissions` to Claude Code |

## Capabilities

On startup the worker detects which CLIs are available:

- `shutil.which("claude")` → reports `claude_code`
- `shutil.which("codex")` → reports `codex`

Both are reported to the gateway on register. Only the primary
capability is used to populate the auto-created tenant model's
`litellm_model` (e.g., `executor/claude_code`).

## Running multiple workers

Each worker registers under a unique `BSGATEWAY_WORKER_NAME`. Register
several with different names (e.g. `mac-claude`, `gpu-codex`) and each
becomes its own routable target in the gateway's routing rules.

## Uninstall

```bash
# Deregister from the gateway UI (Models → delete worker card) then:
rm -rf ~/.bsgateway-worker
```
