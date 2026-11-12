#!/usr/bin/env python3
"""Run the browser tests (tests/browser_*.py) against one built terminal.

    python tests/run_browser.py --demo /tmp/research-demo.html   # synthetic fixtures
    python tests/run_browser.py --live terminal.html             # real collected data

Some tests only make sense for one kind of build; they are listed below.
Everything else is discovered automatically.
"""
import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEMO_ONLY = {'browser_research_release1.py', 'browser_research_release2.py', 'browser_release22.py'}
LIVE_ONLY = {'browser_research_live.py'}

p = argparse.ArgumentParser()
mode = p.add_mutually_exclusive_group(required=True)
mode.add_argument('--demo', action='store_true')
mode.add_argument('--live', action='store_true')
p.add_argument('html')
a = p.parse_args()

skip = LIVE_ONLY if a.demo else DEMO_ONLY
tests = [t for t in sorted(HERE.glob('browser_*.py')) if t.name not in skip]
failed = []
for test in tests:
    print(f'\n== {test.name}', flush=True)
    if subprocess.run([sys.executable, str(test), a.html]).returncode != 0:
        failed.append(test.name)
print(f'\n{len(tests) - len(failed)}/{len(tests)} browser tests passed')
if failed:
    raise SystemExit('FAILED: ' + ', '.join(failed))
