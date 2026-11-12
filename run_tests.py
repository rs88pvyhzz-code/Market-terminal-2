#!/usr/bin/env python3
"""Run every calculation test (test_*.py in the repository root).

Workflows call this instead of listing each file, so a new test can't be
forgotten in one workflow and run in another. Stops with a non-zero exit if any
test fails, and lists every failure rather than stopping at the first.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
tests = sorted(ROOT.glob('test_*.py'))
if not tests:
    raise SystemExit('No test_*.py files found')
failed = []
for test in tests:
    print(f'\n== {test.name}', flush=True)
    if subprocess.run([sys.executable, test.name], cwd=ROOT).returncode != 0:
        failed.append(test.name)
print(f'\n{len(tests) - len(failed)}/{len(tests)} test files passed')
if failed:
    raise SystemExit('FAILED: ' + ', '.join(failed))
