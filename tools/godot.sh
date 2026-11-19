#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ENGINE_BIN="${GODOT_BIN:-$PROJECT_ROOT/.tools/godot-4.7.2/Godot.app/Contents/MacOS/Godot}"
if [[ ! -x "$ENGINE_BIN" ]]; then
  echo "Set GODOT_BIN to your Godot 4.7.2 executable." >&2
  exit 1
fi
exec "$ENGINE_BIN" --path "$PROJECT_ROOT/game" "$@"
