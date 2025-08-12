#!/usr/bin/env bash
# PURPOSE: Wrapper to run Python flex health/queue checks in the correct venv
# DEPENDENCIES: bash, python/venv
# MODIFICATION NOTES: v1.0 initial

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Prefer project venv if present
VENV_BIN=""
if [[ -x "$REPO_ROOT/venv/bin/python" ]]; then
  VENV_BIN="$REPO_ROOT/venv/bin/python"
elif [[ -x "$REPO_ROOT/venv_py311/bin/python" ]]; then
  VENV_BIN="$REPO_ROOT/venv_py311/bin/python"
else
  VENV_BIN="python3"
fi

exec "$VENV_BIN" "$REPO_ROOT/scripts/verification/flex_health_and_queue_check.py" "$@"


