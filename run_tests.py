#!/usr/bin/env python3
"""Standard-library test + integrity runner for this repository.

Runs everything that can be verified locally with ONLY the Python standard library:

  1. Python unit tests: shared import round-trip checker (tests/), Part 2 direct-router
     template structure (tests/part2/), Part 3 code (tests/part3/), the Part 4 Python twin,
     and Part 5 fault-injection.
  2. JSON validity for every *.json file (including the embedded Part 1 template inner JSON).
  3. Reference-path existence: every build_spec / importable_artifact / manifest_candidate
     path named in tracking/assessments.json must exist on disk.
  4. Node detection: if `node` is on PATH, also runs the Part 4 .mjs core test; otherwise it
     is reported as SKIPPED (the Python semantic-parity twin covers the same logic).

Exit code is non-zero if anything fails. No network, no installs, no DevRev APIs.

Usage:  python3 run_tests.py
"""

import json
import os
import shutil
import subprocess
import sys
import unittest

ROOT = os.path.abspath(os.path.dirname(__file__))

PY_TEST_DIRS = [
    "tests",                             # shared: import round-trip checker tests
    "tests/part2",                       # Part 2 direct-router template structure + regex samples
    "tests/part3",                       # Part 3 request/response/reverse/notify unit tests
    "part4-business-hours-snapin/code/test",
    "part5-monitoring-debug/code",
]


def run_python_tests():
    total = 0
    failures = 0
    for rel in PY_TEST_DIRS:
        d = os.path.join(ROOT, rel)
        loader = unittest.TestLoader()
        suite = loader.discover(start_dir=d, pattern="test_*.py", top_level_dir=d)
        print("\n=== python tests: %s ===" % rel)
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        total += result.testsRun
        failures += len(result.failures) + len(result.errors)
    print("\nPython totals: ran %d, failures/errors %d" % (total, failures))
    return failures == 0, total


def check_all_json():
    bad = []
    checked = 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        if ".git" in dirpath:
            continue
        for fn in filenames:
            if fn.endswith(".json"):
                p = os.path.join(dirpath, fn)
                checked += 1
                try:
                    with open(p, encoding="utf-8") as fh:
                        data = json.load(fh)
                except Exception as e:  # noqa: BLE001
                    bad.append((p, str(e)))
                    continue
                # Part 1 template: also parse the stringified inner JSON.
                if isinstance(data, dict) and isinstance(data.get("data"), str):
                    try:
                        json.loads(data["data"])
                    except Exception as e:  # noqa: BLE001
                        bad.append((p + " (inner data)", str(e)))
    print("\n=== JSON validity: checked %d files ===" % checked)
    for p, e in bad:
        print("  BAD:", p, "::", e)
    return len(bad) == 0


def check_reference_paths():
    tracking = os.path.join(ROOT, "tracking", "assessments.json")
    with open(tracking, encoding="utf-8") as fh:
        data = json.load(fh)
    missing = []
    keys = ("importable_artifact", "build_spec", "manifest_candidate")
    for part in data.get("parts", []):
        for k in keys:
            val = part.get(k)
            if isinstance(val, str) and val:
                if not os.path.exists(os.path.join(ROOT, val)):
                    missing.append("%s.%s -> %s" % (part.get("id"), k, val))
    # Also verify every screenshot path referenced in Part 1 evidence exists.
    for part in data.get("parts", []):
        for ev in part.get("evidence_review", []) or []:
            p = ev.get("path")
            if isinstance(p, str) and p and not os.path.exists(os.path.join(ROOT, p)):
                missing.append("%s evidence -> %s" % (part.get("id"), p))
    print("\n=== reference-path existence ===")
    for m in missing:
        print("  MISSING:", m)
    return len(missing) == 0


def run_node_core_test():
    node = shutil.which("node")
    test_file = os.path.join(
        ROOT, "part4-business-hours-snapin", "code", "test", "business_hours.core.test.mjs"
    )
    print("\n=== Part 4 .mjs core test ===")
    if not node:
        print("  SKIPPED: node not on PATH (Python semantic-parity twin covers this logic).")
        return True  # not a failure; twin covers it
    proc = subprocess.run([node, test_file], capture_output=True, text=True)
    print(proc.stdout.strip())
    if proc.returncode != 0:
        print(proc.stderr.strip())
    return proc.returncode == 0


def main():
    ok_py, _ = run_python_tests()
    ok_json = check_all_json()
    ok_refs = check_reference_paths()
    ok_node = run_node_core_test()

    print("\n================ SUMMARY ================")
    print("python tests        :", "PASS" if ok_py else "FAIL")
    print("json validity       :", "PASS" if ok_json else "FAIL")
    print("reference paths      :", "PASS" if ok_refs else "FAIL")
    print("node .mjs core test  :", "PASS/SKIP" if ok_node else "FAIL")
    all_ok = ok_py and ok_json and ok_refs and ok_node
    print("overall             :", "PASS" if all_ok else "FAIL")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
