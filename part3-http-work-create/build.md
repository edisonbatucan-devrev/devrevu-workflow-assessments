# Part 3 - HTTP works.create + reverse severity

**Goal:** Ticket Created (severity `low`) -> build request (Execute Code) -> HTTP POST
`works.create` to create an Issue -> validate response (Execute Code) -> reverse severity and
comment on the created issue -> notify the ticket owner with the new ISS display_id. Org:
`edison-org-for-test`, trigger filtered to a dedicated Part 3 test part AND severity == `low`.

> **Status:** Prepared - sandbox build / live validation pending. The HTTP and notification
> node import/export shapes are **not verified** for this org, so there is no importable
> template; build in the Workflow Builder UI from `build.json`. The Execute Code node bodies in
> `code/` are runnable and tested (`tests/part3/test_part3.py`).
>
> **Endpoint note:** the exercise says `work.create`; the real DevRev endpoint is
> `works.create`. Use `https://api.devrev.ai/works.create`.

## Files

- `build.json` - the full node-by-node UI build map (configuration only, not importable).
- `code/build_request.py` - builds the works.create body with `json.dumps` + `external_ref`.
- `code/validate_response.py` - raises on non-2xx / missing IDs; never leaks the body/token.
- `code/reverse_severity.py` - validates the lowercase enum, then reverses the severity string.
- `code/notify_policy.py` - gates "notify only after a verified create" and produces the exact
  notification + comment bodies (prevents the duplicate-create footgun; no network call).

## Build steps

1. **Ticket Created** - filter: Part 3 test part + severity `low`. REQUIRED before publish.
2. **Execute Code: build_request** - inputs bound from the trigger (`id`, `title`,
   `applies_to_part.id`, `owned_by` mapped to an ids array, `severity`). Outputs `body`,
   `external_ref`.
3. **HTTP POST** `https://api.devrev.ai/works.create`:
   - Auth: **active sandbox Auth Token connection**, header `Authorization: Bearer ...`. Never
     paste a raw token anywhere.
   - Header `Content-Type: application/json`; body = `$get('build_request','output').body`.
   - Payload: `type=issue`, `title`=ticket title, `applies_to_part`=ticket
     `applies_to_part.id`, `owned_by`=owner id array, `external_ref`=`devrevu-p3:<ticket id>`.
   - **Duplicates:** `external_ref` *mitigates* duplicates but is not exactly-once. Prefer
     check-before-create on that `external_ref`, or handle a 409 explicitly. Do NOT blind-retry.
   - Capture `status_code` + full JSON body in the node outputs.
4. **Execute Code: validate_response** - raises on non-2xx or missing `work.id` /
   `work.display_id`, so a non-2xx HTTP "finish" becomes a **failed run**. Confirm the real
   response field path from an **actual captured sandbox response** and configure
   `work_id` / `display_id` outputs from that real shape.
5. **Execute Code: reverse_severity** - validate lowercase (`low`/`high`/`medium`/`blocker`)
   then reverse (`low` -> `wol`).
6. **Add Comment on the created ISSUE** - object = validated `work_id`, internal, body =
   reversed severity.
7. **Add Comment on the TICKET** - internal, references the new ISS display_id.
8. **(Optional) Link Ticket to Issue** - if a link operation is available in your org.
9. **Notify the ticket owner** - "`<ISS display_id>` has been created for your ticket." using
   the real `display_id` (`notify_policy.py` builds the message).

## Test matrix

| # | Scenario | Expected |
|---|----------|----------|
| 1 | low-severity ticket, valid token | 2xx, issue created once, reversed-severity comment on issue, ticket comment, owner notified |
| 2 | non-low ticket | workflow does not run (filter) |
| 3 | HTTP returns non-2xx (e.g. bad field) | validate_response raises -> run FAILED (not silent success) |
| 4 | response missing ids | validate_response raises -> run FAILED |
| 5 | re-trigger same ticket | external_ref present; verify no duplicate (check-before-create / 409 handling) |

## Prerequisites & calibration

- Sandbox `edison-org-for-test`; a dedicated **Part 3 test part**; an active **Auth Token
  connection** (Bearer) stored as a workflow connection - never pasted into any file; the
  Execute Code nodes pasted from `code/`.
- **First-run calibration:** capture a **real** `works.create` response in the sandbox and set
  the `validate_response` field path for `work_id`/`display_id` from that real shape. There is
  no committed sample response - do not infer the shape, verify it live.

## Evidence

Save real screenshots in `screenshots/` per `checklist.md` (mask the token). Record the real
response field path and display_ids in the checklist; never commit real object ids or tokens.
