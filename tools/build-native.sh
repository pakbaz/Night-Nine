#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_VERSION="$(python3 - "$PROJECT_ROOT/game/project.godot" <<'PY'
import re,sys
from pathlib import Path
match=re.search(r'config/version="(\d+\.\d+\.\d+)[^\"]*"',Path(sys.argv[1]).read_text())
if not match:raise SystemExit('Set a semantic project version before packaging.')
print(match[1])
PY
)"
for BUILD_PLATFORM in macOS Windows-x64; do
  if [[ -f "$PROJECT_ROOT/builds/NightNine-$BUILD_VERSION-$BUILD_PLATFORM.zip" ]]; then
    echo "Preserve the existing $BUILD_VERSION package; select a new project version." >&2
    exit 2
  fi
done
mkdir -p "$PROJECT_ROOT/builds/macos" "$PROJECT_ROOT/builds/windows" "$PROJECT_ROOT/tmp/qa"
bash "$PROJECT_ROOT/tools/godot.sh" --headless --editor --import --quit --log-file "$PROJECT_ROOT/tmp/qa/build-import.log"
bash "$PROJECT_ROOT/tools/godot.sh" --headless --script res://tests/collect_licenses.gd --log-file "$PROJECT_ROOT/tmp/qa/licenses.log"
bash "$PROJECT_ROOT/tools/godot.sh" --headless --export-release "macOS" --log-file "$PROJECT_ROOT/tmp/qa/export-mac.log"
bash "$PROJECT_ROOT/tools/godot.sh" --headless --export-release "Windows Desktop" --log-file "$PROJECT_ROOT/tmp/qa/export-windows.log"
python3 "$PROJECT_ROOT/tools/check-log.py" "$PROJECT_ROOT/tmp/qa/build-import.log" "$PROJECT_ROOT/tmp/qa/licenses.log" "$PROJECT_ROOT/tmp/qa/export-mac.log" "$PROJECT_ROOT/tmp/qa/export-windows.log"
if command -v ditto >/dev/null 2>&1; then
  ditto -c -k --sequesterRsrc --keepParent "$PROJECT_ROOT/builds/macos/Night Nine.app" "$PROJECT_ROOT/builds/NightNine-$BUILD_VERSION-macOS.zip"
fi
python3 "$PROJECT_ROOT/tools/package-windows.py"
python3 "$PROJECT_ROOT/tools/package-desktop-source.py"
