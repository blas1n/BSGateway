#!/usr/bin/env bash
# BSGateway Worker Installer
# Usage:
#   curl -fsSL http://<gateway-origin>/api/v1/workers/install.sh | bash
#
# Environment variables:
#   BSGATEWAY_SERVER_URL    (auto-injected by the server when you fetch this)
#   BSGATEWAY_INSTALL_TOKEN (required on first run — mint one via the gateway UI:
#                           Models → Install Worker → Generate Token)
#   INSTALL_DIR             (default: ~/.bsgateway-worker)

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-$HOME/.bsgateway-worker}"
BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

info()   { printf '%b\n' "${GREEN}▸${NC} $*"; }
warn()   { printf '%b\n' "${YELLOW}▸${NC} $*"; }
error()  { printf '%b\n' "${RED}✕${NC} $*" >&2; }
header() { printf '\n%b\n' "${BOLD}$*${NC}"; }

# ─── Prerequisites ────────────────────────────────────────────────

header "BSGateway Worker Installer"
echo ""

check_cmd() {
    if ! command -v "$1" &>/dev/null; then
        error "$1 not found."
        echo "  $2"
        return 1
    fi
    info "$1 found: $(command -v "$1")"
}

MISSING=0
check_cmd python3 "Install Python 3.11+: https://python.org" || MISSING=1

# At least one of claude / codex is required
HAS_CLI=0
command -v claude &>/dev/null && { info "claude found: $(command -v claude)"; HAS_CLI=1; }
command -v codex  &>/dev/null && { info "codex  found: $(command -v codex)";  HAS_CLI=1; }
if [ "$HAS_CLI" -eq 0 ]; then
    error "Neither claude nor codex CLI found."
    echo "  Install one of:"
    echo "    npm install -g @anthropic-ai/claude-code"
    echo "    npm install -g @openai/codex"
    MISSING=1
fi

HAS_UV=0
if command -v uv &>/dev/null; then
    info "uv found: $(command -v uv)"
    HAS_UV=1
else
    warn "uv not found (optional, will use pip instead)"
    warn "  Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

if [ "$MISSING" -eq 1 ]; then
    echo ""
    error "Missing prerequisites. Install them and re-run."
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]; }; then
    error "Python 3.11+ required, found $PY_VERSION"
    exit 1
fi
info "Python $PY_VERSION"

# ─── Install ──────────────────────────────────────────────────────

header "Installing to $INSTALL_DIR"

mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# SERVER_URL is injected by the /workers/install.sh endpoint before serving.
SERVER_URL="${BSGATEWAY_SERVER_URL:-}"

if [ -z "$SERVER_URL" ]; then
    error "BSGATEWAY_SERVER_URL is not set."
    error "  Run: BSGATEWAY_SERVER_URL=http://<gateway-origin> bash install.sh"
    exit 1
fi

info "Downloading worker source from $SERVER_URL..."
if curl -fsSL "$SERVER_URL/api/v1/workers/source.tar.gz" -o /tmp/bsgateway-worker.tar.gz; then
    tar xzf /tmp/bsgateway-worker.tar.gz -C "$INSTALL_DIR"
    rm -f /tmp/bsgateway-worker.tar.gz
    info "Downloaded worker source"
else
    error "Failed to download worker source from $SERVER_URL"
    exit 1
fi

# Install dependencies
if [ "$HAS_UV" -eq 1 ]; then
    info "Installing with uv..."
    uv venv --quiet 2>/dev/null || true
    uv pip install --quiet -e .
else
    info "Installing with pip..."
    python3 -m pip install --quiet -e .
fi

# ─── Shell wrapper ────────────────────────────────────────────────

WRAPPER="$INSTALL_DIR/bsgateway-worker"
cat > "$WRAPPER" << WRAPPER_SCRIPT
#!/usr/bin/env bash
cd "$INSTALL_DIR"
if command -v uv &>/dev/null && [ -d "$INSTALL_DIR/.venv" ]; then
    exec uv run python -m worker "\$@"
else
    exec python3 -m worker "\$@"
fi
WRAPPER_SCRIPT
chmod +x "$WRAPPER"

# Persist server URL to .env (for subsequent runs)
cat > "$INSTALL_DIR/.env" << ENV_FILE
BSGATEWAY_SERVER_URL=$SERVER_URL
ENV_FILE

# ─── Done ─────────────────────────────────────────────────────────

header "Installation complete!"
printf '\n'
printf '  Next step — start the worker:\n'
printf '\n'
printf '     %bBSGATEWAY_INSTALL_TOKEN=<paste-install-token> %s/bsgateway-worker%b\n' "$BOLD" "$INSTALL_DIR" "$NC"
printf '\n'
printf '  Mint an install token in the gateway UI:\n'
printf '     Models → Install Worker → Generate Token\n'
printf '\n'
printf '  After first run the worker token is saved to %s/.env\n' "$INSTALL_DIR"
printf '  and subsequent runs need no token argument.\n\n'
