# Part 3 - HTTP node + external integration (Intermediate)

**Goal:** Ticket Created (severity `low`) -> build request (Execute Code) -> HTTP POST
`works.create` to create an Issue -> validate response (Execute Code) -> reverse severity
and comment on the created issue -> notify the ticket owner with the new ISS display_id.

**Org:** `edison-org-for-test`. Trigger filtered to a dedicated Part 3 test part AND
severity == `low`.

> **Endpoint note:** the exercise says `work.create`; the real DevRev endpoint is
> `works.create`. We use `https://api.devrev.ai/works.create`.

## Why this ships as a build-spec
HTTP node and notification node import/export shapes are **not verified** for this org. The
authoritative artifact is `build-specs/part3-http-work-create.build-spec.json`. The Execute
Code and comment steps have known shapes and runnable code.

## Files
- `code/build_request.py` - builds the works.create body with `json.dumps` + `external_ref`.
- `code/validate_response.py` - raises on non-2xx / missing IDs; never leaks body/token.
- `code/reverse_severity.py` - validates then reverses the severity string.
- `code/test_part3.py` - unittests (run them).
- `build-specs/part3-http-work-create.build-spec.json` - full UI build map.
- `build-specs/sample-response.PLACEHOLDER.json` - synthetic; replace with real capture.

## Build steps

1. **Ticket Created** - filter: Part 3 test part + severity `low`. REQUIRED before publish.
2. **Execute Code: build_request** - inputs bound from trigger (`id`, `title`,
   `applies_to_part.id`, `owned_by` mapped to ids array, `severity`). Outputs `body`,
   `external_ref`.
3. **HTTP POST** `https://api.devrev.ai/works.create`:
   - Auth: **active sandbox Auth Token connection**, header `Authorization: Bearer ...`.
     Never paste a raw token anywhere.
   - Header `Content-Type: application/json`.
   - Body = `$get('build_request','output').body`.
   - Payload: `type=issue`, `title`=ticket title, `applies_to_part`=ticket
     `applies_to_part.id`, `owned_by`=owner id array, `body`=synthetic reference,
     `external_ref`=`devrevu-p3:<ticket id>`.
   - **Duplicates:** `external_ref` *mitigates* duplicates but is not exactly-once. Prefer
     checking for an existing work with that `external_ref` before creating, or handle a
     409 conflict explicitly. **Do not blindly POST-retry.**
   - Capture `status_code` + full JSON body in node outputs.
4. **Execute Code: validate_response** - raises on non-2xx or missing `work.id` /
   `work.display_id`, so a non-2xx HTTP "finish" becomes a **failed run**. Confirm the real
   response field path from an **actual captured sandbox response** and configure
   `work_id` / `display_id` outputs from that real shape (see sample placeholder).
5. **Execute Code: reverse_severity** - validate lowercase (`low`/`high`/`medium`/`blocker`)
   then reverse (`low` -> `wol`).
6. **Add Comment on the created ISSUE** - object = validated `work_id`, internal, body =
   reversed severity.
7. **Add Comment on the TICKET** (required by screenshot asks) - internal, references the
   new ISS display_id.
8. **(Optional) Link Ticket to Issue** - supported enhancement if a link op is available.
9. **Notify the ticket owner** - "`<ISS display_id>` has been created for your ticket."
   using the real `display_id`.

## Per-step field mapping

| Node | Field | Value |
|------|-------|-------|
| build_request | ticket_id/title/applies_to_part_id/owned_by_ids/severity | from trigger |
| HTTP | URL | `https://api.devrev.ai/works.create` |
| HTTP | Authorization | `Bearer` via sandbox connection (no raw token) |
| HTTP | Content-Type | `application/json` |
| HTTP | body | `$get('build_request','output').body` |
| validate_response | status_code / response_body | from HTTP node |
| reverse_severity | severity | trigger `.severity` |
| comment (issue) | object | `$get('validate_response','output').work_id` |
| comment (ticket) | object | `$get('ticket_created_1','output').id` |
| notify | message | `<display_id> has been created for your ticket.` |

## Test matrix

| # | Scenario | Expected |
|---|----------|----------|
| 1 | low-severity ticket, valid token | 2xx, issue created once, reversed-severity comment on issue, ticket comment, owner notified |
| 2 | non-low ticket | workflow does not run (filter) |
| 3 | HTTP returns non-2xx (e.g. bad field) | validate_response raises -> run FAILED (not silent success) |
| 4 | response missing ids | validate_response raises -> run FAILED |
| 5 | re-trigger same ticket | external_ref present; verify no duplicate (check-before-create / 409 handling) |

## Manual sandbox execution & testing

Built in the UI from `build-specs/part3-http-work-create.build-spec.json` (HTTP +
notification shapes are not importable here). Live-run after building.

- **Prerequisites:** sandbox `edison-org-for-test`; a dedicated **Part 3 test part**; an
  active **Auth Token connection** (Bearer) stored as a workflow connection - never pasted
  into any file; the Execute Code nodes pasted from `code/`.
- **Settings to confirm before publish:** trigger filter Part = Part 3 test part **and**
  severity `low`; HTTP URL `https://api.devrev.ai/works.create`; `Content-Type:
  application/json`; Authorization via the Bearer connection; body =
  `$get('build_request','output').body`; HTTP node captures `status_code` + full JSON body.
- **First-run calibration:** capture a **real** `works.create` response in the sandbox and
  set the `validate_response` field path for `work_id`/`display_id` from that real shape
  (replace `build-specs/sample-response.PLACEHOLDER.json`, which is synthetic).
- **Trigger / event:** create a **low-severity** ticket in the Part 3 test part.
- **Sample input & expected outputs:** low-severity ticket, valid token -> 2xx; issue created
  once; reversed-severity comment on the issue (`low` -> `wol`); comment on the ticket
  referencing the new `ISS-` display_id; owner notified "`<ISS display_id>` has been created
  for your ticket."
- **Negative / edge cases:**
  - Non-low ticket -> workflow does not run (filter).
  - HTTP returns non-2xx (bad field) -> `validate_response` raises -> run **FAILED** (not a
    silent success).
  - Response missing ids -> `validate_response` raises -> run **FAILED**.
  - Re-trigger same ticket -> `external_ref` present; confirm **no duplicate issue**
    (check-before-create or explicit 409 handling); do not blind-retry.
- **Evidence (save in `screenshots/`, see `screenshots/CHECKLIST.md`, mask the token):**
  `workflow-config.png`, `ticket-and-issue-comments.png`, `events-tab-history.png`. Record
  the real response field path and display_ids in the checklist.
