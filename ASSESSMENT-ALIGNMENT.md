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

## Part 2 - Advanced workflow nodes (Intermediate)  -  local-prepared (candidate); live import PENDING

Current candidate: the **direct Ask AI -> Router** template (no Execute Code steps). Build/verify
notes in `part2-ai-classify-router/build.md`.

| Requirement (exact) | File / path | Status |
|---|---|---|
| Triggered when a ticket is created | `part2-ai-classify-router/templates/11-Part 2-direct-router.template.json` (`ticket_created_1`) | local-prepared |
| Ask AI classifies into Bug / Feature / Enhancement | same template `ask_ai_1` (two-line prompt embedded in the template) | local-prepared (Ask AI import shape not independently verified) |
| Router branches into **3 named paths** | template `router_1` - **exactly 3 routes** Bug/Feature/Enhancement (no 4th), matched by JSONata `$match` regex on the AI output | local-prepared (live Router/`$match` unverified) |
| Bug: set severity **High** | `update_ticket_1` (`update_ticket`, `high`) | local-prepared |
| Bug: validate title format via regex | native `if_else_1` JSONata `$match` on `^\[BUG\] .{5,120}$` (no Execute Code) | local-prepared |
| Bug: post internal comment if invalid | `add_comment_4` (`add_comment`, `internal`) on the `if_else_1` false port | local-prepared |
| Feature / Enhancement: set severity **Medium** | `update_ticket_2` / `update_ticket_3` (`medium`) | local-prepared |
| Each accepted path: classification justification comment | `add_comment_1/2/3` (all `internal`) | local-prepared |

Design notes (documented, not deviations from the exercise):
- No Execute Code nodes: Bug-title validation is a native JSONata `$match` regex in an `if_else`
  condition, and each Router route matches a full category-specific AI response via `$match`.
- Malformed AI output matches no route and performs no branch action - a Completed run with no
  route taken is **not** success; inspect the actual AI output and route in the Runs tab.
- Untrusted title/body are delimited (`<ticket_title>` / `<ticket_body>`) and treated as DATA in
  the Ask AI prompt. Bug title format is a stated lab convention, not an assessment requirement.
- **Not verified:** a LIVE sandbox import, dynamic Router port behavior, and JSONata `$match`
  evaluation. Do not publish / call import-ready until a live import + Validate succeed.
- Local proof: `tests/part2/test_direct_router_template.py` asserts Ask AI wired directly to the
  Router, exactly 3 routes with matching ports, no `invoke_code`/validator references,
  reachable/acyclic, no dangling `$get`, Bug=high and the other two `update_ticket` steps=medium,
  severity enum lowercase, single `if_else` with true/false ports, internal comments, no
  hardcoded DON, plus Python equivalents of the routing/Bug-title regex samples.

## Part 3 - HTTP node and external integration (Intermediate)  -  local-prepared

| Requirement | File / path | Status |
|---|---|---|
| Triggered on ticket created with **low** severity | `part3-http-work-create/build.json` (trigger filter: Part 3 test part + severity `low`) | local-prepared |
| HTTP node calls `work.create` API to create an Issue, passing the ticket title | `code/build_request.py` (maps exercise `work.create` -> real `works.create`, `type=issue`, `title`); `build.json` HTTP node | local-prepared (real response shape must be captured in sandbox) |
| Execute Code reverses severity `low` -> `wol`, adds it as a comment on the created issue | `code/reverse_severity.py` + `code/notify_policy.py` (issue comment) | local-prepared |
| Notify ticket owner `{{ISS-ID}} has been created for your ticket.` | `code/notify_policy.py` - `"<display_id> has been created for your ticket."`; placeholders mapped, never fake IDs | local-prepared |
| Deliverables (config, comments, Events tab) | `checklist.md` | manual-pending |

Optional guards retained (safe-on-bad-input stops that do not alter the required happy path):
`validate_response.py` (429/409 handling), `verify_conflict_is_same_source`, notify-before-
verify gate. `validate_endpoint` rejects the Part 5 typo path and non-HTTPS/wrong host.

## Part 4 - Snap-in development (Advanced)  -  local-verified; live deploy/run NOT verified

| Requirement | File / path | Status |
|---|---|---|
| Snap-in with custom operation (3P node) "Business Hour Validator" | `part4-business-hours-snapin/code/manifest.example.yaml` (`display_name: Business Hour Validator`) | local-verified (manifest remotely validated; NOT deployed) |
| `manifest.yaml` with operation inputs/outputs | `manifest.example.yaml` - inputs `org_schedule_id`,`timestamp`; outputs `is_within_business_hours`,`next_open_time`,`evaluated_at` | local-verified (named `.example` on purpose; not an active manifest) |
| TypeScript function implementing the logic | `code/src/core/business_hours.core.ts` (+ `.mjs` + Python twin); `code/src/functions/business_hours_validator/index.ts` | local-verified (`npm run build` compiles clean against SDK v1.1.79; core 18 + adapter 12 + Python twin 17 pass, all MOCKED) |
| Declare scopes for `org-schedules.evaluate/get/list` | `manifest.example.yaml` scope `org_schedule:read` | local-verified (manifest + scopes **remotely** validated "Manifest is valid" Oct 12 2026; not a deploy) |
| Within hours -> live agent; outside hours -> auto-reply `We're currently offline. We'll get back to you at {{next_open_time}}.` | `BUILD-GUIDE.md` workflow section + `workflow.build-spec.json` | local-prepared (auto-reply text matches); live run manual-pending |
| Test locally and **deploy** | `BUILD-GUIDE.md` build/deploy steps marked "not run here" | local tests done; **deploy/live run manual-pending** |

Honest distinction: the TypeScript adapter + core now **compile locally** against the
installed `@devrev/typescript-sdk` v1.1.79, and the core (18), adapter (12), and Python twin
(17) tests pass - but these are **SIMULATED/MOCKED** (in-memory fake schedule, injected
`fetch`), not a live evaluation. The manifest/scopes passed a **remote** server-side validation
(not part of the strictly-local proof). The actual `snap_in_version` create/deploy and the live
Conversation Created workflow run are **NOT done** and not claimed. No DevRevU LMS/certification
is claimed.

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

`python3 run_tests.py` -> **107 Python tests pass**, 0 failures; 8 JSON files valid;
reference paths exist; Part 4 `.mjs` SKIPPED (no Node; Python twin covers it). Per-suite:
shared round-trip checker = 10, Part 2 (direct-router template) = 22, Part 3 = 52,
Part 4 (Python twin) = 17, Part 5 = 6. See `tracking/test-execution-report.md`.

## What is explicitly NOT done
- No workflow deployed, no live run, no screenshots captured by this process.
- No live import / Validate for the Part 2 direct-router template; dynamic Router ports and
  JSONata `$match` evaluation are unverified.
- Part 1 priority-field update not verified. Part 4 compiles and tests locally (MOCKED) and
  its manifest/scopes passed a remote validation, but the snap-in is **not deployed** and the
  live workflow was **not run**.
- No git commit/push; no org tools/APIs invoked.
