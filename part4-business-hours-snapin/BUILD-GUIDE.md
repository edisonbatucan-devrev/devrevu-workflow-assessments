# Part 4 - Snap-in: Business Hours Validator (Advanced)

**Goal:** A snap-in with a custom operation (3P node) that receives a timestamp and tells a
workflow whether it is within the org's business hours, plus the next opening time. Used in
a Conversation Created workflow that routes to a live agent (within hours) or sends an
auto-reply (outside hours).

**Org:** `edison-org-for-test`. Needs an Org Schedule (e.g. Mon-Fri 09:00-18:00
**Asia/Manila** lab default) and an active PLuG/email channel. Conversation trigger must be
filtered to a dedicated test channel.

## What is complete vs. needs deployment
- **Core business logic:** `src/core/business_hours.core.mjs` + the `.ts` twin. These are the
  deployed artifacts. Because the authoring environment has **no Node.js**, the `.mjs` tests
  (`test/business_hours.core.test.mjs`) could **not be executed here**. A **Python
  semantic-parity twin** (`test/business_hours_core.py`) reimplements the identical algorithm
  and **is actually run** (`test/test_business_hours_core.py`, 17 passing tests), covering the
  same scenarios: within/outside hours, bounded transition following, weekend/holiday,
  undefined/unknown definedness failure, schedule-unavailable, timeout/abort, DST-boundary,
  and active-with-closing-transition.
- **Candidate, NOT compiled/validated here:** the SDK adapter
  (`src/functions/business_hours_validator/index.ts`) and `manifest.example.yaml` (named
  `.example` so it is not mistaken for a deploy-ready manifest). No snap-in toolchain / SDK is
  installed in the authoring environment, so these were not compiled or CLI-validated. Items
  needing confirmation are flagged `VERIFY` / `TODO(VERIFY-SCOPES)`.

## org-schedules.evaluate contract used
- Request: `{ id, instants: [timestamp] }`
- Response: `{ instant_evaluations: [ { at, definedness, is_active, next_transition } ] }`
- When `is_active` is false, `next_transition` is a **candidate** next opening. The core
  **follows transitions and re-evaluates** to verify an actually-active instant, with a
  **bounded loop** (`MAX_TRANSITION_HOPS = 8`). It **never invents** a next time: if it
  can't verify an opening, `next_open_time` is empty.
- Schedule expired/unavailable/empty response -> a **schedule error** (code
  `schedule_unavailable`), explicitly **not** treated as "offline".
- An evaluation whose `definedness` is **not** `defined` (e.g. `undefined`/`unknown`, or
  missing without an explicit boolean `is_active`) raises a **schedule error** (code
  `schedule_undefined`). The core does **not** guess "offline" when the schedule does not
  cover the instant.
- When `is_active` is **true**, `next_transition` is the **closing** time; the core returns an
  **empty** `next_open_time` and never surfaces the closing time as an opening.
- Timestamp is validated (offset-aware); bad or offset-less input raises `bad_timestamp`.

## Operation I/O
- Inputs: `org_schedule_id` (text), `timestamp` (text).
- Outputs: `is_within_business_hours` (bool), `next_open_time` (text, empty if active),
  `evaluated_at` (text).

## Adapter notes (confirm before deploy)
- SDK imports from `@devrev/typescript-sdk/dist/snap-ins`: `FunctionInput`,
  `ExecuteOperationInput`, `OperationOutput`, `Error_Type` (and `OperationBase`).
- Output via `OperationOutput.fromJSON({ output: { values: [result] } })`; errors are
  structured.
- Event accessors used: `event.payload.data` (VERIFY against the runtime adapter),
  `event.execution_metadata.devrev_endpoint`, `event.context.secrets.service_account_token`.
- HTTP timeout is bounded (8s); the service account token is never logged; error messages
  never include the response body.

## Build & deploy steps (sandbox)
1. `npm install` (installs TypeScript + the DevRev SDK) then `devrev snap_in_version create`
   from this `code/` dir. **This step was not run here.**
2. Resolve `TODO(VERIFY-SCOPES)`: set the real `service_account.scopes.self` scope and any
   operation `static_scopes` for org-schedules, using the API-to-scope reference, then CLI
   validate. Do not deploy with fabricated scopes.
3. Deploy to `edison-org-for-test`.
4. Build the Conversation Created workflow (see `workflow.build-spec.json`).

## The workflow (build-spec)
See `workflow.build-spec.json`. Trigger: Conversation Created (dedicated test channel) ->
validator operation on `conversation.created_date` -> If/Else on
`is_within_business_hours`:
- **true** -> route to the live group/agent (use a REAL live group/agent in the sandbox).
- **false** -> external auto-reply: "We're currently offline. We'll get back to you at
  `<next_open_time>`." - include the time **only if present** (non-empty).
- **error** -> internal diagnostic comment; do **not** claim "offline" inaccurately.

## Test matrix (local core tests already cover the logic)

| # | Scenario | Expected |
|---|----------|----------|
| 1 | timestamp within hours | is_within=true, next_open empty, route to agent |
| 2 | timestamp outside hours (evening) | is_within=false, verified next_open, auto-reply with time |
| 3 | weekend | is_within=false; next_open only if verified, else empty |
| 4 | holiday (multi-hop until open) | is_within=false, next_open = first verified open |
| 5 | expired/unavailable schedule | schedule error (NOT offline) -> diagnostic branch |
| 6 | invalid timestamp | schedule error (bad_timestamp) -> diagnostic branch |
| 7 | malformed response / HTTP timeout | schedule error -> diagnostic branch, no credential leak |
| 8 | undefined/unknown definedness | schedule error (schedule_undefined), NOT offline |
| 9 | DST boundary (mocked server transitions) | follows server transitions; never computes wall-clock offsets itself |

Run the tests:
- With Node (the deployed core): `node test/business_hours.core.test.mjs`
- Without Node (semantic-parity twin, runs anywhere Python 3.9+ is present):
  `cd test && python3 -m unittest test_business_hours_core -v`

Note: in this authoring environment Node was not available, so only the Python twin was
executed. Run the `.mjs` suite in your own environment before relying on the deployed core.

## Manual sandbox execution & testing

This part is a **candidate snap-in**: the SDK adapter and `manifest.example.yaml` are **not
compiled or CLI-validated here**. Validate and deploy before any live run - do not deploy
with the fabricated/candidate scopes.

- **Prerequisites:** sandbox `edison-org-for-test`; Node 18+ and the DevRev CLI
  (`devrev snap_in`); an **Org Schedule** (lab default Mon-Fri 09:00-18:00 Asia/Manila); an
  active PLuG/email channel; a dedicated **test channel** for the Conversation trigger; a
  service-account token stored as a secret (never pasted into a file).
- **Validate before deploy (must pass first):**
  1. `npm install` then `npm run build` (compile the TS adapter).
  2. `node test/business_hours.core.test.mjs` (run the `.mjs` core suite - the Python twin
     already passed here).
  3. Resolve `TODO(VERIFY-SCOPES)` in `manifest.example.yaml`; CLI-validate; copy to
     `manifest.yaml`; `devrev snap_in_version create`; deploy.
- **Settings to confirm:** the custom operation registered with inputs `org_schedule_id`,
  `timestamp`; the Conversation Created trigger filtered to the test channel; If/Else on
  `is_within_business_hours`.
- **Trigger / event:** create a conversation in the test channel (Conversation Created);
  the operation evaluates `conversation.created_date`.
- **Sample inputs & expected outputs:**
  - Timestamp within hours -> `is_within=true`, `next_open_time` empty, route to the live
    group/agent.
  - Timestamp outside hours (evening/weekend) -> `is_within=false`, verified `next_open_time`,
    external auto-reply including the time only if present.
- **Negative / edge cases:**
  - Expired/unavailable schedule -> schedule error (**NOT** "offline") -> diagnostic branch.
  - Invalid/offset-less timestamp -> `bad_timestamp` error -> diagnostic branch.
  - Malformed response / HTTP timeout -> schedule error, no credential leak.
  - `undefined`/`unknown` definedness -> `schedule_undefined` error, NOT "offline".
- **Evidence (save in `screenshots/`, see `screenshots/CHECKLIST.md`):**
  `node-in-action-list.png`, `node-config-panel.png`, `workflow-ifelse-on-output.png`,
  `run-within-hours.png`, `run-outside-hours.png`. Record the Org Schedule id and routed
  group/agent in the checklist.
