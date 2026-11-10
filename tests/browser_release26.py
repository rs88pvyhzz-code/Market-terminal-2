"""Compatibility entry point: Release 2.7 replaces the superseded ETF interface."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('browser_release27.py')),run_name='__main__')
