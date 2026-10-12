# Part 3 - HTTP works.create + reverse severity

**Goal:** Ticket Created (severity `low`) -> build request (Execute Code) -> HTTP POST
`works.create` to create an Issue -> validate response (Execute Code) -> reverse severity and
comment on the created issue -> notify the ticket owner with the new ISS display_id. Org:
`edison-org-for-test`, trigger filtered to a dedicated Part 3 test part AND severity == `low`.

> **Status:** Import **draft generated** - live import/run **UNVERIFIED**. A full v2 workflow
> template is generated at `templates/12-Part 3-template.json` (by `tools/gen_template.py`),
> with every node shape grounded in the public `shashankcube/computer-skill`
> create-workflow-template v2 examples (envelope + `invoke_code` + `http` + `add_comment` +
> `if_else` + `send_notification`). It has **not** been imported or run against any org, so do
> not treat it as live-verified; the `works.create` response field path for `work.id`/
> `display_id` is also unverified and must be confirmed against a real sandbox capture.
> `build.json` remains the node-by-node build map; the Execute Code bodies in `code/` are
> runnable and tested (`tests/part3/test_part3.py`), and the template embeds grounded copies of
> them plus the default-safe guards described below.
>
> **Endpoint note:** the exercise says `work.create`; the real DevRev endpoint is
> `works.create`. Use `https://api.devrev.ai/works.create`.

## Importable template & default-safe guards

- **Template:** `templates/12-Part 3-template.json` (also copied into the conversation workdir
  as a Canvas attachment). Regenerate with
  `python3 part3-http-work-create/tools/gen_template.py "part3-http-work-create/templates/12-Part 3-template.json"`.
- **Flow (all native, grounded steps):** Ticket Created -> `build_request` (Execute Code,
  preflight) -> **HTTP POST** `works.create` (Bearer) -> `validate_response` (Execute Code,
  raises on non-2xx) -> `reverse_severity` -> comment on created issue -> comment on ticket ->
  `notify_policy` (Execute Code) -> native `if_else` gate -> `send_notification` (true branch
  only; false branch ends safely).
- **No side effects by default.** The template is a draft and both live creation and
  notifications are OFF until you explicitly opt in:
  - `build_request` top constants: `ALLOW_LIVE_CREATE=False`, `EXPECTED_PART_ID=''`,
    `EXPECTED_TEST_OWNER_ID=''`. The node **raises before the HTTP call** unless you set
    `ALLOW_LIVE_CREATE=True`, set `EXPECTED_PART_ID` to your sandbox Part 3 part DON, and the
    ticket owner matches `EXPECTED_TEST_OWNER_ID` and severity is `low`. This stops a published
    workflow from firing for *every* low-severity ticket.
  - `notify_policy` top constants: `ALLOW_OWNER_NOTIFICATION=False`, `EXPECTED_TEST_OWNER_ID=''`.
    It outputs `should_notify=False` unless you enable the flag **and** the ticket owner equals
    `EXPECTED_TEST_OWNER_ID`. The native `if_else` gate only routes to `send_notification` when
    `should_notify` is true, so notifications are skipped by default (not merely empty
    recipients). No secret belongs in any of these constants.
- **Auth:** the HTTP node's Bearer auth **connection is selected in the UI after import** - no
  raw token is stored in the template or this repo. `enable_retries=false`; there is no loopback
  into the create node.
- **Duplicate mitigation:** the body carries `external_ref` `devrevu-p3:<ticket id>`. This
  *mitigates* duplicates but is **not** an exactly-once or 409 guarantee; verify behavior in the
  sandbox.

## How to test (import draft -> configure -> validate -> publish)

1. **Import the draft:** import `templates/12-Part 3-template.json` into the Workflow Builder in
   `edison-org-for-test`. (Live import is unverified - if a node fails to import, fall back to
   `build.json` to build it in the UI, and report the gap.)
2. **Configure test IDs + connection (no token pasting):** on the HTTP node select an active
   sandbox **Bearer Auth Token connection** (never paste a raw token). In `build_request` set
   `ALLOW_LIVE_CREATE=True`, `EXPECTED_PART_ID=<your sandbox Part 3 part DON>`,
   `EXPECTED_TEST_OWNER_ID=<your own user DON>`. In `notify_policy` set
   `ALLOW_OWNER_NOTIFICATION=True` and the same `EXPECTED_TEST_OWNER_ID`. Filter the trigger to
   that part AND severity `low`.
3. **Validate:** capture a real `works.create` response and confirm the `work.id`/`display_id`
   field path used by `validate_response`; dry-run with the guards OFF first (the preflight
   should block before any HTTP call).
4. **Publish only after guards are set,** then fire **one** low-severity test ticket owned by you
   on the Part 3 part. Confirm: issue created once, reversed-severity comment on the issue, ISS
   reference comment on the ticket, and (only because you enabled it) one notification to you.

## Files

- `templates/12-Part 3-template.json` - generated importable v2 template (**import draft, live
  import/run UNVERIFIED**).
- `tools/gen_template.py` - deterministic generator for that template (shapes grounded in the
  public v2 examples; embeds the Code bodies + default-safe guards).
- `build.json` - the full node-by-node UI build map (fallback / reference).
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
