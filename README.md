# devrevu-workflow-assessments

Codebase for the **DevRevU "Advanced Workflow Exercise"** (Parts 1-5): workflow templates,
build guides, build-spec JSON, runnable code + tests, a candidate snap-in, and assessment
tracking. Sandbox org for all live work: `edison-org-for-test`
(https://app.devrev.ai/edison-org-for-test).

---

## 1. Start here - what this repo is (and is not)

- It **is** a local, public-safe deliverable: everything is file/code, built with synthetic
  placeholders. No tokens, no real object IDs, no internal doc dumps.
- It **is not** a set of deployed, live-validated workflows. Only **Part 1** is confirmed
  complete (by Edison) - though the exercise's **priority-field update** is not satisfied by the
  starter template (it is omitted and must be added in the sandbox against a real priority
  field), so that sub-requirement is **manual-pending**, not verified.
- **Part 2 is a direct Ask AI -> Router candidate:** Ticket Created -> Ask AI -> Router with
  **exactly 3 named routes** (Bug/Feature/Enhancement), **no Execute Code steps**. Bug ->
  severity High + a native JSONata `$match` regex title check + internal invalid-title comment.
  Feature/Enhancement -> severity Medium. Internal classification-justification comment on each
  accepted path. This is **locally graph-validated only** - a live sandbox import, dynamic
  Router ports, and JSONata regex evaluation are **UNVERIFIED**; nothing here claims it imports
  or runs. **Parts 3-5 are "Prepared - sandbox build/live validation pending"**.
- No official DevRevU LMS pass/score is recorded here, because none was provided.
- See `ASSESSMENT-ALIGNMENT.md` for a per-requirement checklist (requirement -> file -> status).

Package vs deployed, at a glance:

| Part | In this repo | Status | Needs a human in the sandbox |
|------|--------------|--------|------------------------------|
| 1 - Severity branching | Importable draft-starter template + guide + screenshots | **Completed (user-confirmed)** | Non-blocker comment + real priority-field screenshots to finish the optional checklist |
| 2 - AI classify + Router | Direct Ask AI -> Router candidate template (`templates/11-Part 2-direct-router.template.json`, exactly 3 routes, native JSONata `$match` regex, no Code steps) + `build.md` + `checklist.md`; structure/regex tests in `tests/part2/` | **Prepared (candidate) - live import/validation pending** | Import the template, Validate (confirm Ask AI -> Router + 3 ports + `$match` conditions), re-export and run the round-trip check, then live-test |
| 3 - HTTP works.create | request builder / response validator / reverse / notify-gate (`code/` + 52 tests in `tests/part3/`), `build.md` + `build.json` | Prepared | Capture real response shape, deploy, live-test, screenshots |
| 4 - Business Hours snap-in | core (`.mjs`+`.ts`) + Python twin + SDK adapter + standard entrypoint; builds locally against SDK v1.1.79 (core 18 + adapter 12 + Python twin 17, all MOCKED); manifest remotely validated | Local-verified; deploy/live run pending | Deploy (`snap_in_version create`), live-test the Conversation Created workflow, add screenshots |
| 5 - Monitoring/debug | fault-injection build-spec + Python fault/recovery tests (6 tests) | Prepared | Inject fault on a Part 3 copy, debug, fix, screenshots |

## 2. Run the tests (standard library only)

```bash
python3 run_tests.py
```

Runs all Python suites, validates every JSON file (including the Part 1 template's embedded
inner JSON), checks that every path referenced in `tracking/assessments.json` exists, and runs
the Part 4 `.mjs` core test **if** Node is installed. Expected: `overall : PASS` with 107
Python tests. Exact commands and recorded results are in `tracking/test-execution-report.md`.

Per-suite, if you prefer:

```bash
python3 -m unittest discover -s tests        -p 'test_*.py' -v   # shared round-trip checker
python3 -m unittest discover -s tests/part2  -p 'test_*.py' -v   # Part 2 direct-router template
python3 -m unittest discover -s tests/part3  -p 'test_*.py' -v   # Part 3 code
( cd part4-business-hours-snapin/code/test && python3 -m unittest test_business_hours_core -v )
( cd part5-monitoring-debug/code && python3 -m unittest test_fault_injection -v )
# Part 4 deployed core (needs Node 18+; the Python twin above covers the same logic):
node part4-business-hours-snapin/code/test/business_hours.core.test.mjs
```

## 3. Safety rules this package follows

- **File/code only** - no org queries, no APIs/tokens, nothing deployed while producing this.
- **Sandbox only** - all live work belongs in `edison-org-for-test`.
- **Dedicated test part/channel per trigger** - every ticket-created / conversation-created
  trigger must be filtered to a dedicated test part/channel *before publishing*, or it fires
  on every new object in the org. Starter templates carry this warning in their `description`.
- **Public-repo safety** - synthetic samples/placeholders only; `.gitignore` excludes `.env`,
  tokens, caches and build dirs; `.DS_Store`/`__pycache__` are not committed.

## 4. Why some parts are build maps, not importable files

The import/export field shapes for the **HTTP and notification** nodes (Part 3) and the
snap-in (Part 4) are **not verified** for this org. Rather than ship importable files that
would silently fail or mislead, those are delivered as clearly-labeled **build maps**
(`part3-http-work-create/build.json`, `part4-business-hours-snapin/workflow.build-spec.json`,
`part5-monitoring-debug/build-specs/fault-injection.build-spec.json`) describing exactly what
to configure in the Workflow Builder. The Part 1 and Part 2 workflows ship as importable
`*.template.json` wrappers; the Part 2 direct-router template is a **candidate whose live
import is unverified** (see `part2-ai-classify-router/build.md`).

Template wrapper format: `{ "data": "<stringified inner JSON>", "templateVersion": "2.0.0" }`,
where the inner JSON holds `description`, `serialization_version {2,0,0}`, `steps[]`, `title`.
`text_template` expressions use the DevRev `{% expr ... %}` markers.

## 5. Prerequisites for live work

Sandbox (`edison-org-for-test`): dedicated test part(s) for Parts 1-3; a test channel for
Part 4; an Org Schedule for Part 4; a sandbox API token stored as a workflow *connection*
(Part 3 Bearer) and a service-account token secret (Part 4) - **never** pasted into any file;
and a real exposed priority field for Part 1.

Local toolchain: Python 3.9+ (standard library). Optional: Node 18+ and `tsc` for the Part 4
TypeScript; DevRev CLI (`devrev snap_in`) for Part 4 validate/deploy (not run here).

## 6. Layout

```
README.md                     <- this file
IMPROVEMENTS.md               <- what changed in this revision + remaining live prerequisites
run_tests.py                  <- standard-library test + integrity runner
.gitignore
tools/                        <- shared helpers (check_import_roundtrip.py)
tests/                        <- centralized Python tests: test_import_roundtrip.py, part2/, part3/
tracking/                     <- assessments.json, assessment-tracker.md, test-execution-report.md
part1-ticket-severity-branch/ <- importable template + guide + screenshots (Edison-confirmed)
part2-ai-classify-router/     <- build.md + checklist.md + direct-router template + screenshots
part3-http-work-create/       <- build.md + checklist.md + build.json + request/response/reverse/notify code
part4-business-hours-snapin/  <- core (.mjs/.ts) + Python twin + tests + candidate manifest/adapter
part5-monitoring-debug/       <- fault-injection build-spec + fault/recovery tests
```

## 7. Publishing

Making the repo public is required by the assessment. Before doing so, confirm `.gitignore`
excludes `.env`/tokens/build dirs (it does), that no real org IDs/tokens/internal exports were
pasted anywhere, and that every draft-starter template still carries its trigger-filter warning.
