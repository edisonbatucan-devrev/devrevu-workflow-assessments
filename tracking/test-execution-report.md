# Test execution report

All results below were produced locally with the Python standard library only. No network,
no installs, no DevRev APIs, nothing deployed. Git baseline: `origin/main` @ `1ab6111`
("Updated part1").

## One command to reproduce everything

```bash
python3 run_tests.py
```

This runs the Python suites, validates every JSON file (including the Part 1 template's
embedded inner JSON), checks that every path referenced in `tracking/assessments.json` exists,
and runs the Part 4 `.mjs` core test if Node is present.

Observed summary:

```
python tests        : PASS   (107 ran, 0 failures/errors)
json validity       : PASS   (8 files)
reference paths     : PASS
node .mjs core test : SKIPPED (node not on PATH; Python twin covers the same logic)
overall             : PASS
```

## Per-suite commands and results

Tests are centralized under `tests/` (Part 2 template + shared tools) and `tests/part2`,
`tests/part3`; Parts 4-5 keep their suites in-place.

| Suite | Command | Result |
|-------|---------|--------|
| shared round-trip checker | `python3 -m unittest discover -s tests -p 'test_*.py'` | Ran 10 tests - OK (synthetic unittests for `tools/check_import_roundtrip.py`, incl. a `literal`->`text_template` value-type regression) |
| Part 2 direct-router template | `python3 -m unittest discover -s tests/part2 -p 'test_*.py'` | Ran 22 tests - OK (`test_direct_router_template.py`: Ask AI -> Router wiring, EXACTLY 3 routes with matching ports, no `invoke_code`/validator refs, reachable/acyclic, no dangling `$get`, Bug=high + two medium, single if_else true/false ports, internal comments, no hardcoded DON, plus Python equivalents of the routing/Bug-title regex samples) |
| Part 3 code | `python3 -m unittest discover -s tests/part3 -p 'test_*.py'` | Ran 52 tests - OK |
| Part 4 (Python twin) | `cd part4-business-hours-snapin/code/test && python3 -m unittest test_business_hours_core` | Ran 17 tests - OK |
| Part 5 | `cd part5-monitoring-debug/code && python3 -m unittest test_fault_injection` | Ran 6 tests - OK |

Total: **107 Python tests**, 0 failures/errors.

## Import round-trip checker

`tools/check_import_roundtrip.py` compares an EXPECTED workflow template against an
EXPORTED-after-import template and fails on dropped/extra/duplicate keys, changed signatures
(incl. a changed embedded Code body or a `literal`<->`text_template` value-type flip),
missing/changed edges, or dangling `$get` references. Its 10 synthetic unittests
(`tests/test_import_roundtrip.py`) PASS and are part of the 107 above. This is a LOCAL
structural check only - it does NOT simulate the DevRev importer and is NOT proof of live
import compatibility. After a live Part 2 import, re-export the template and run the checker
(candidate vs re-export); it must PASS before relying on the template.

## Part 4 Node test status

`node` was **not** available in the authoring environment, so
`part4-business-hours-snapin/code/test/business_hours.core.test.mjs` was **NOT executed here**.
A Python semantic-parity twin (`business_hours_core.py` + `test_business_hours_core.py`) mirrors
the same algorithm and scenarios and DID run (17 tests). Run the `.mjs` suite in a Node 18+
environment before relying on the deployed TypeScript core:

```bash
node part4-business-hours-snapin/code/test/business_hours.core.test.mjs
```

## TypeScript compile status

`tsc` / `npx` were not available either, so the TypeScript core and SDK adapter were **not
compiled** here. The `.ts` core is kept hand-synced with the tested `.mjs`/Python twin; the SDK
adapter (`index.ts`) and `manifest.example.yaml` remain explicit CANDIDATES (see their VERIFY /
TODO markers) pending a Node + `@devrev/typescript-sdk` + DevRev CLI environment.

## What is NOT asserted here

- No live workflow run, no deployment, no screenshots captured by this process.
- No official DevRevU LMS pass/score. Part 1 completion is recorded from Edison's explicit
  confirmation only (see `assessments.json` -> part1.completion).
- Parts 2-5 are "Prepared - sandbox build/live validation pending".
