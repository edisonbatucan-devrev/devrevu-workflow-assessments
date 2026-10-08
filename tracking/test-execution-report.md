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
python tests        : PASS   (159 ran, 0 failures/errors)
json validity       : PASS   (10 files)
reference paths     : PASS
node .mjs core test : SKIPPED (node not on PATH; Python twin covers the same logic)
overall             : PASS
```

## Per-suite commands and results

| Part | Command | Result |
|------|---------|--------|
| 2 | `python3 -m unittest discover -s part2-ai-classify-router/code -p 'test_*.py'` | Ran 84 tests - OK (classification + title validators, derived-route tests, and the Part 2 template-structure suite `test_part2_template.py`) |
| 3 | `python3 -m unittest discover -s part3-http-work-create/code -p 'test_*.py'` | Ran 52 tests - OK |
| 4 (Python twin) | `cd part4-business-hours-snapin/code/test && python3 -m unittest test_business_hours_core` | Ran 17 tests - OK |
| 5 | `cd part5-monitoring-debug/code && python3 -m unittest test_fault_injection` | Ran 6 tests - OK |

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
