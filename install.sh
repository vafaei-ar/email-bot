#!/usr/bin/env bash
# Create .venv, install dependencies, copy example config if missing, optional credential prompts, run the bot.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PYTHON_CMD="${PYTHON:-python3}"
if ! command -v "$PYTHON_CMD" >/dev/null 2>&1; then
  echo "Error: '${PYTHON_CMD}' not found. Install Python 3.10+ and try again." >&2
  exit 1
fi

VENV="$ROOT/.venv"
if [[ ! -d "$VENV" ]]; then
  echo "Creating virtual environment in .venv ..."
  "$PYTHON_CMD" -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"

python -m pip install -q --upgrade pip
python -m pip install -q -r "$ROOT/requirements.txt"

if [[ ! -f "$ROOT/config.yaml" ]]; then
  cp "$ROOT/config.example.yaml" "$ROOT/config.yaml"
  echo "Created config.yaml from config.example.yaml — edit email filters and telegram.chat_id."
fi
if [[ ! -f "$ROOT/credentials.yaml" ]]; then
  cp "$ROOT/credentials.example.yaml" "$ROOT/credentials.yaml"
  echo "Created credentials.yaml from credentials.example.yaml."
fi

python "$ROOT/scripts/bootstrap_credentials.py"

RUN=1
for arg in "$@"; do
  if [[ "$arg" == "--no-run" ]]; then
    RUN=0
  fi
done

if [[ "$RUN" -eq 1 ]]; then
  echo "Starting bot (Ctrl+C to stop) ..."
  exec python "$ROOT/run.py"
else
  echo "Skipping run. Next time: source .venv/bin/activate && python run.py"
fi
