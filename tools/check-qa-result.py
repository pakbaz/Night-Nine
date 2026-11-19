#!/usr/bin/env python3
"""Require a newly produced completion report, even if a game exits cleanly early."""
import json
import sys
from pathlib import Path
path=Path(sys.argv[1])
minimum=int(sys.argv[2])
if not path.exists():
    raise SystemExit('QA did not produce a completion report: '+str(path))
result=json.loads(path.read_text())
if result.get('failures') or result.get('checks',0)<minimum:
    raise SystemExit('QA completion check failed: '+json.dumps(result))
print('Verified completion report: '+str(path))
