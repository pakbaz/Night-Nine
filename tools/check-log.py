"""Fail automation on engine errors even when Godot exits with status zero."""
import re
import sys
from pathlib import Path

for name in sys.argv[1:]:
    text = Path(name).read_text(errors="replace")
    problems = [line for line in text.splitlines() if re.search(r"(?:SCRIPT ERROR:|^ERROR:)", line)]
    if problems:
        print("\n".join(problems), file=sys.stderr)
        raise SystemExit(1)
