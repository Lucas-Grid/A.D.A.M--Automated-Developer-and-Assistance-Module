"""Stdlib test runner for Jarvis (no pytest required).

Discovers every ``test_*.py`` in this directory, runs every ``test_*``
callable, and reports pass/fail. Each test uses plain ``assert`` — failures
raise AssertionError, which the runner catches and tallies.

Usage:
    python tests/run_tests.py            # run everything
    python tests/run_tests.py test_editfile  # run one module (by file stem)
    python tests/run_tests.py -v         # verbose per-test output
"""
from __future__ import annotations

import glob
import importlib.util
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
sys.path.insert(0, PROJECT)

VERBOSE = "-v" in sys.argv
ONLY = next((a for a in sys.argv[1:] if not a.startswith("-")), None)
if ONLY and ONLY.startswith("test_"):
    ONLY = ONLY[len("test_"):]  # accept 'test_live' or 'live'


def _load(modpath: str):
    name = "jarvis_test_" + os.path.splitext(os.path.basename(modpath))[0]
    spec = importlib.util.spec_from_file_location(name, modpath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    files = sorted(glob.glob(os.path.join(HERE, "test_*.py")))
    if ONLY:
        files = [f for f in files if os.path.splitext(os.path.basename(f))[0] == "test_" + ONLY]
    total = passed = failed = 0
    failures = []
    for f in files:
        mod = _load(f)
        tests = [getattr(mod, n) for n in dir(mod) if n.startswith("test_") and callable(getattr(mod, n))]
        for t in tests:
            total += 1
            try:
                t()
                passed += 1
                if VERBOSE:
                    print(f"  ok   {t.__name__}")
            except AssertionError as e:
                failed += 1
                failures.append((f, t.__name__, str(e) or "assertion"))
                print(f"  FAIL {t.__name__}: {e}")
            except Exception as e:  # noqa: BLE001
                failed += 1
                failures.append((f, t.__name__, repr(e)))
                print(f"  FAIL {t.__name__}: {type(e).__name__}: {e}")
                if VERBOSE:
                    traceback.print_exc()
    print(f"\n{total} tests: {passed} passed, {failed} failed")
    if failures:
        print("\nFailures:")
        for f, n, why in failures:
            print(f"  - {os.path.basename(f)}::{n}: {why}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
