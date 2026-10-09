# Assessment alignment checklist

This maps every requirement of the refreshed "Advanced Workflow Exercise" to the real file(s)
in this repo and a status. Status legend:

- `local-prepared` - artifact exists and is locally structure/unit-tested; no live run.
- `import-blocked` - the artifact is a candidate whose live import/round-trip is not verified.
- `manual-pending` - requires a human in the sandbox (deploy, screenshot, or real field).
- `user-confirmed` - Edison explicitly confirmed completion.

Nothing here is deployed, committed, or pushed. Sandbox org for all live work:
`edison-org-for-test`. No real exported private DON IDs are copied into public files; the
source exercise text is paraphrased, not copied wholesale.

---

## Part 1 - Workflow fundamentals (Beginner)  -  user-confirmed (one gap)

| Requirement | File / path | Status |
|---|---|---|
| Triggered when a ticket is created | `part1-ticket-severity-branch/templates/10-Part 1-template.json` | user-confirmed (canvas screenshot) |
| Control (If/Else) on severity | same template + `part1-.../BUILD-GUIDE.md` | user-confirmed |
| Blocker: **update the ticket priority field** | starter template **omits** the priority step; `BUILD-GUIDE.md` step 3 insists on a REAL priority field (not `priority_v2`) | **manual-pending** - NOT verified; priority is NOT a severity substitute and must be added in the sandbox |
| Blocker: internal comment mentioning creator via `{{ variables }}` | `10-Part 1-template.json` (comment uses dynamic creator mention); `screenshots/image-2.png` | user-confirmed (resolved `@edison-batucan`) |
| Other severities: a different comment | template false branch; `BUILD-GUIDE.md` | local-prepared (no non-blocker ticket screenshot) |
| Deploy, test tickets, Runs tab | `screenshots/image.png`, `image-1.png` (WORKFLOW-10 / TKT-11 Completed) | user-confirmed |

Note: Part 1 export/screenshots are preserved exactly; the only correction is the explicit
record that the priority-field update is not yet verified.

## Part 2 - Advanced workflow nodes (Intermediate)  -  local-prepared / import-blocked

| Requirement (exact) | File / path | Status |
|---|---|---|
| Triggered when a ticket is created | `part2-ai-classify-router/templates/11-Part 2-template.json` (`ticket_created_1`) | local-prepared |
| Ask AI classifies into Bug / Feature / Enhancement | same template `ask_ai_1`; prompt `part2-.../prompts/classification-prompt.md` | local-prepared (Ask AI import shape not independently verified) |
| Router branches into **3 named paths** | template `router_1` - **exactly 3 routes** Bug/Feature/Enhancement (no 4th) | local-prepared (import-blocked for live Router shape) |
| Bug: set severity **High** | `bug_set_severity` (`update_ticket`, `high`) | local-prepared |
| Bug: validate title format via Execute Code / regex | `bug_validate_title` (`invoke_code`); `code/title_validator.py` | local-prepared |
| Bug: post internal comment if invalid | `bug_invalid_comment` (`add_comment`, `internal`) via `bug_title_if_else` | local-prepared |
| Feature / Enhancement: set severity **Medium** | `feature_set_severity` / `enhancement_set_severity` (`medium`, **unconditional**, no gate) | local-prepared |
| All paths: classification justification comment | `bug_/feature_/enhancement_justification_comment` (all `internal`) | local-prepared |

Design notes (documented, not deviations from the exercise):
- The Execute Code validator runs **before** the Router. On a clean in-enum result it emits
  `route` = the accepted label; on **any** malformed/unknown/empty output it **raises
  `ValueError`**, which stops the run (shown as a failed run in the Runs tab). This keeps the
  Router at exactly 3 routes and prevents any severity mutation on bad AI output - there is no
  4th "Review" path. Strict entrypoint: `run_strict` in `code/classification_validator.py`.
- The validator never uses `eval`/`exec` and never runs JSONata `$eval` on the untrusted AI
  string. Untrusted title/body are delimited and treated as DATA in the Ask AI prompt.
- An **optional** non-failing Review-emitting variant (`validate_classification`/`run`) is
  retained in the module and documented as a non-default safety alternative.
- **Not verified:** the Code `input_values`/`output_schema` field shapes are the reference-docs
  candidate; the Ask AI/Router export shapes are not independently verified; a LIVE sandbox
  import + re-export round-trip has NOT been run. Do not publish/call import-ready.
- Local proof: `code/test_part2_template.py` (115-test Part 2 suite incl. this file) asserts
  exactly 3 routes, validator code raises `ValueError`, Feature/Enhancement set medium with no
  gate, Bug sets high, text_template code fields, reachable/acyclic, no dangling `$get`,
  internal comments, severity enum, no hardcoded DON. `code/test_classification_validator.py`
  asserts the strict function returns an enum route and raises on invalid.

## Part 3 - HTTP node and external integration (Intermediate)  -  local-prepared

| Requirement | File / path | Status |
|---|---|---|
| Triggered on ticket created with **low** severity | `part3-http-work-create/build-specs/part3-http-work-create.build-spec.json` (trigger filter low) | local-prepared |
| HTTP node calls `work.create` API to create an Issue, passing the ticket title | `code/build_request.py` (maps exercise `work.create` -> real `works.create`, `type=issue`, `title`); build-spec HTTP node | local-prepared (real response shape must be captured in sandbox) |
| Execute Code reverses severity `low` -> `wol`, adds it as a comment on the created issue | `code/reverse_severity.py` + `code/notify_policy.py` (issue comment) | local-prepared |
| Notify ticket owner `{{ISS-ID}} has been created for your ticket.` | `code/notify_policy.py` - `"<display_id> has been created for your ticket."`; placeholders mapped, never fake IDs | local-prepared |
| Deliverables (config, comments, Events tab) | `screenshots/CHECKLIST.md` | manual-pending |

Optional guards retained (safe-on-bad-input stops that do not alter the required happy path):
`validate_response.py` (429/409 handling), `verify_conflict_is_same_source`, notify-before-
verify gate. `validate_endpoint` rejects the Part 5 typo path and non-HTTPS/wrong host.

## Part 4 - Snap-in development (Advanced)  -  import-blocked / manual-pending

| Requirement | File / path | Status |
|---|---|---|
| Snap-in with custom operation (3P node) "Business Hour Validator" | `part4-business-hours-snapin/code/manifest.example.yaml` (`display_name: Business Hour Validator`) | import-blocked (candidate manifest, NOT deployed) |
| `manifest.yaml` with operation inputs/outputs | `manifest.example.yaml` - inputs `org_schedule_id`,`timestamp`; outputs `is_within_business_hours`,`next_open_time`,`evaluated_at` | import-blocked (candidate shape, named `.example` on purpose) |
| TypeScript function implementing the logic | `code/src/core/business_hours.core.ts` (+ tested `.mjs` + Python twin); `code/src/functions/business_hours_validator/index.ts` | local-prepared (TS not compiled here - no `tsc`/Node) |
| Declare scopes for `org-schedules.evaluate/get/list` | `manifest.example.yaml` candidate scope `org_schedule:read`, marked `TODO(VERIFY-SCOPES)` | import-blocked - exact scope slug NOT confirmed |
| Within hours -> live agent; outside hours -> auto-reply `We're currently offline. We'll get back to you at {{next_open_time}}.` | `BUILD-GUIDE.md` workflow section + `workflow.build-spec.json` | local-prepared (auto-reply text matches) |
| Test locally and **deploy** | `BUILD-GUIDE.md` build/deploy steps marked "This step was not run here." | manual-pending (candidate vs actual manifest; not deployed) |

Honest distinction: the `.mjs`/Python core logic is unit-tested here (17 Python-twin tests);
the SDK adapter + manifest are explicit **candidates** pending a Node + `@devrev/typescript-sdk`
+ DevRev CLI environment. The actual deployed manifest/scopes are not claimed. Testing of live
hours and offline-time text is specified in the BUILD-GUIDE test matrix.

## Part 5 - Monitoring and debugging (Bonus)  -  local-prepared / manual-pending

| Requirement | File / path | Status |
|---|---|---|
| Reuse any workflow from Parts 1-3 | `part5-monitoring-debug/BUILD-GUIDE.md` (uses a sandbox COPY of Part 3) | local-prepared |
| Intentionally introduce an error | `build-specs/fault-injection.build-spec.json` (wrong HTTP path / injected raise) | local-prepared |
| Find failed run in Runs tab; inspect node I/O; use AI error explanation (sparkle/star button) | `BUILD-GUIDE.md` | manual-pending |
| Fix, publish a new version, verify success | `BUILD-GUIDE.md`; `code/test_fault_injection.py` (6 tests, reuses Part 3 `validate_response`) | local-prepared / manual-pending |

Preserve: the intentional-fail -> inspect -> fix-new-version flow and screenshots.

---

## Tests

`python3 run_tests.py` -> **190 Python tests pass**, 0 failures; 11 JSON files valid;
reference paths exist; Part 4 `.mjs` SKIPPED (no Node; Python twin covers it). Per-suite:
Part 2 = 115, Part 3 = 52, Part 4 (Python twin) = 17, Part 5 = 6. See
`tracking/test-execution-report.md`.

## What is explicitly NOT done
- No workflow deployed, no live run, no screenshots captured by this process.
- No live import / re-export round-trip for Part 2; the Code field shapes are candidates.
- Part 1 priority-field update not verified; Part 4 snap-in not deployed and scope slugs not
  confirmed.
- No git commit/push; no org tools/APIs invoked.
