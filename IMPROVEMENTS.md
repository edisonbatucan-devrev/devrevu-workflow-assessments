# Improvements in this revision

Branch `improve-assessments-2-5`, based on `origin/main` @ `1ab6111`. This revision (1) fixes
stale Part 1 tracking and (2) brings Parts 2-5 into the repo and hardens their code - it does
more than copy the earlier candidates. Nothing is deployed, committed, or pushed by this work.

## Part 1 - tracking corrected (workflow + screenshots preserved exactly)

The Part 1 workflow template and the three screenshots are **unchanged**. Only the tracking was
fixed:

- `importable_artifact` now points at the real file
  `part1-ticket-severity-branch/templates/10-Part 1-template.json` (was a stale
  `7-Workflow fundamentals-template.json` that does not exist on this baseline).
- All references to a non-existent `image-3.png` were removed.
- Evidence is **re-described from the actual screenshot content** (workflow "Part 1", **v1**
  Active; run **WORKFLOW-10 / TKT-11** Completed; a correctly-rendered `@edison-batucan`
  mention). The earlier notes about **TKT-9 / v2 / a literally-rendered expression** are kept
  only as *historical observations* and are **not** silently re-associated to these refreshed
  same-name screenshots.
- The hundreds of repetitive `not_individually_confirmed` subtask rows were collapsed into a
  concise optional `acceptance_checklist` with real statuses (`live`/`prepared`/`pending`),
  preserving the semantics and Edison's confirmed completion. Reviewer/run links stay `null`.

## Part 2 - AI classification gate hardened

- `_coerce_structured` now **strictly rejects** Markdown code fences (```` ```json ```` ),
  prose-prefixed/trailing output, and any non-object JSON - with a documented reason, not an
  incidental parse error. Field values are never eval'd/executed.
- New tests: fenced/bare-fence/prose-wrapped rejection; label injected as list/number/null/
  nested object; adversarial instructions inside the justification are treated as inert data;
  attempted label override via justification has no effect. **63 tests pass** (was 52).

## Part 3 - HTTP create/notify hardened

- New `validate_endpoint` enforces the fixed **HTTPS** `https://api.devrev.ai/works.create`
  endpoint (rejects http://, wrong host, embedded credentials, alternate path incl. the Part 5
  typo). `build_request.run` returns the validated endpoint.
- `validate_response` now distinguishes **429 (rate_limited)** and **409 (conflict)** via a
  `WorksCreateError.code`, so the workflow can branch without blind in-node retries.
  `verify_conflict_is_same_source` permits reusing an existing issue **only** when its
  `external_ref` matches this ticket's - never an unrelated issue. No exactly-once is claimed.
- New `notify_policy.py` separates create from notify: it refuses to notify/comment unless the
  issue is verified created (so a failed notify cannot loop back and create a **duplicate**
  issue), and produces the exact "`ISS-ID` has been created for your ticket." text.
- New tests: endpoint validation, unsafe unicode/quotes encoding, invalid owners, 404/409/429/
  bad-status/bad-response codes, conflict same-source reuse, notify gate. **52 tests pass**
  (was 23). Error messages still never leak the body/token.

## Part 4 - Business Hours core hardened + runnable twin

- Both `.mjs` and `.ts` cores now check `definedness`: an `undefined`/`unknown` (or missing
  without an explicit boolean `is_active`) evaluation **raises** `schedule_undefined` instead of
  guessing "offline". Active-with-`next_transition` still returns an empty `next_open_time`
  (that transition is the closing time). Transition following stays bounded and never fabricates
  a next opening; schedule-unavailable and timeouts raise rather than mislabel offline.
- Because **Node is not installed** in the authoring environment, the `.mjs` tests could not be
  run here. A **Python semantic-parity twin** (`code/test/business_hours_core.py` +
  `test_business_hours_core.py`, **17 tests, run and passing**) mirrors the algorithm and adds
  undefined/unknown-definedness, timeout/abort, and DST-boundary cases. The `.mjs` suite was
  extended with the same cases for when Node is available.
- `manifest.yaml` -> **`manifest.example.yaml`** with an explicit "not a deploy-ready manifest"
  note. The SDK adapter and manifest scopes remain explicit CANDIDATES (VERIFY / TODO markers).

## Part 5 - real local fault-injection + recovery tests

- New `part5-monitoring-debug/code/test_fault_injection.py` (**6 tests, passing**) **reuses
  Part 3's `validate_response`** (no duplicated comment/notify logic). It proves the injected
  fault raises (non-2xx 404 and injected `raise`; the typo endpoint is rejected by the Part 3
  allow-list) and that the fix recovers against a **synthetic** 2xx response.

## Repo hygiene & tooling

- Added `run_tests.py` (standard-library runner + JSON/reference-path integrity checks) and a
  full `README.md` (basic -> deep, package-vs-deployed) and this `IMPROVEMENTS.md`.
- Added `.gitignore` (excludes `.env`/tokens/caches/build dirs); removed the three tracked
  `.DS_Store` files for a clean public repo.
- Corrected `text_template` markers in the Part 2/3/4 build-specs from `<% expr %>` to the
  DevRev `{% expr %}` convention (the same defect fixed in the Part 1 template).

## Remaining live prerequisites (none done here - require a human in the sandbox)

- Part 1: non-blocker-comment and real priority-field screenshots to close the optional checklist.
- Part 2: build Ask AI + Router in the UI from the build-spec; live-test Bug/Feature; screenshots.
- Part 3: capture a real `works.create` response and configure the HTTP output mapping; set up a
  Bearer connection; live-test; screenshots.
- Part 4: resolve candidate scopes, `snap_in init`, compile TS, CLI-validate the manifest, deploy,
  configure an Org Schedule + test channel, live-test within/outside hours; screenshots.
- Part 5: inject the fault on a Part 3 copy, capture the failed run + AI explanation, fix, publish,
  verify success; screenshots.
