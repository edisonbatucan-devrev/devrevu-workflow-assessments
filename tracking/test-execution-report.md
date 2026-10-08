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
python tests        : PASS   (190 ran, 0 failures/errors)
json validity       : PASS   (11 files)
reference paths     : PASS
node .mjs core test : SKIPPED (node not on PATH; Python twin covers the same logic)
overall             : PASS
```

## Per-suite commands and results

| Part | Command | Result |
|------|---------|--------|
| 2 | `python3 -m unittest discover -s part2-ai-classify-router/code -p 'test_*.py'` | Ran 115 tests - OK (classification validator incl. the ALIGNED strict `validate_classification_strict`/`run_strict` - returns an enum route and RAISES ValueError on invalid; the optional Review-emitting variant; title validator; the aligned template-structure suite `test_part2_template.py` - EXACTLY 3 routes, no 4th Review route, validator code raises ValueError, Feature/Enhancement set medium with no gate, Bug sets high, text_template code fields, no dangling `$get`; the import round-trip checker suite `test_import_roundtrip.py`) |
| 3 | `python3 -m unittest discover -s part3-http-work-create/code -p 'test_*.py'` | Ran 52 tests - OK |
| 4 (Python twin) | `cd part4-business-hours-snapin/code/test && python3 -m unittest test_business_hours_core` | Ran 17 tests - OK |
| 5 | `cd part5-monitoring-debug/code && python3 -m unittest test_fault_injection` | Ran 6 tests - OK |

## Part 2 import round-trip check (EXPECTED failure on the real export)

`part2-ai-classify-router/code/check_import_roundtrip.py` compares an EXPECTED template
against an EXPORTED-after-import template. Its 10 synthetic unittests
(`test_import_roundtrip.py`, now including a `literal`->`text_template` value-type regression)
are part of the 115 Part 2 tests above and PASS.

Running the checker on the **real** failed export the user provided is a diagnostic, not a
unit test, and it is **EXPECTED to exit 1** - that non-zero exit is the evidence of the import
loss, NOT a `run_tests.py` failure:

```bash
python3 part2-ai-classify-router/code/check_import_roundtrip.py \
  Part2-corrected-template.json "14-Part 2-template.json" \
  --report Part2-import-comparison.json
# -> exit 1
```

Observed: 5 dropped reference keys (`validate_classification`, `bug_validate_title`,
`bug_justification_comment`, `feature_justification_comment`,
`enhancement_justification_comment`), 10 missing edges, and 2 dangling `$get` reference
families (`validate_classification`, `bug_validate_title`). The expected/exported sample
files and the written `Part2-import-comparison.json` live at the workdir root (kept out of the
repo for reproducibility; the original export file is unchanged). This is a LOCAL structural
comparison only - it does NOT simulate the DevRev importer and is NOT proof of live import
compatibility.

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
