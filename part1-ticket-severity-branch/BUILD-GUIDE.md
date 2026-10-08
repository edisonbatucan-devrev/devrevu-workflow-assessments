# Part 1 - Workflow fundamentals: severity branching

**Goal:** Ticket Created -> If/Else on severity. On `blocker`: update the ticket priority
and post an internal comment mentioning the creator with a variable. On all other
severities: post a different comment. Deploy, create test tickets, verify in Runs tab.

**Org:** `edison-org-for-test` only. Trigger must be filtered to a dedicated Part 1 test part.

## What's in this folder
- `templates/part1-severity-branch.DRAFT-STARTER.template.json` - importable **draft
  starter** with the known steps (trigger, If/Else, two internal comments). It
  **deliberately omits** the priority-update step because the real priority field for this
  org is not verified. It is not safe to publish until you complete the steps below.
- `screenshots/CHECKLIST.md` - exactly which screenshots the assessment wants.

## Step-by-step build (Workflow Builder UI)

### Step 0 - Create a dedicated test part
Create (or reuse) a part named e.g. `Part 1 Test` so the trigger does not fire on every
ticket in the org.

### Step 1 - Ticket Created trigger
- Operation: `devrev` / `ticket_created`.
- **Trigger filter: set Part = your Part 1 Test part.** REQUIRED before publishing.
- Trigger output fields available downstream (verified): `id`, `display_id`, `severity`
  (lowercase string), `created_by.id`, `applies_to_part.id`, `owned_by` (array of user
  objects), `title`, `body`, `created_date`.

### Step 2 - If/Else on severity
- Operation: `devrev` / `if_else`.
- Input field `condition` (literal), nested group shape:

```json
{
  "conditions": [
    { "conditions": [
        { "type": "rule",
          "operands": [
            { "type": "jsonata_expression", "value": "$get('ticket_created_1', 'output').severity" },
            { "type": "literal", "value": ["blocker"] }
          ],
          "operator": "contains_any" }
      ],
      "logical_operator": "and", "negate": false, "type": "group" }
  ],
  "logical_operator": "and", "negate": false, "type": "group"
}
```

> **Note on operator:** `contains_any` with the one-element array `["blocker"]` matches the
> exact severity enum. An exact `equals` operator spelling was not verified for this org,
> so `contains_any` is used intentionally. Severity values are lowercase strings
> (`blocker`, `high`, `medium`, `low`).

- `true` port -> blocker branch. `false` port -> other branch.

### Step 3 (blocker branch) - Update priority  **[UI STEP YOU MUST ADD - field choice required]**
- Operation: `devrev` / `update_ticket`.
- `id` = `$get('ticket_created_1', 'output').id` (jsonata).
- **Priority field:** `update_ticket` inputs `id`, `title`, `severity` are **verified**.
  A `priority` input was **NOT verified / not exposed** in this org. **Do not invent a
  `priority_v2` field.** In the sandbox, open the Update Ticket node and pick whatever real
  **priority** or **custom priority** field is actually exposed on tickets, and set it to
  the escalated value (e.g. "P1"/"Highest" per your org's enum). Record the exact field
  name/value you used in `screenshots/CHECKLIST.md`.
- If no priority field is exposed at all, document that and (as a verified fallback) also
  bump `severity` to the highest exposed value - but the assessment asks specifically for
  *priority*, so prefer a real priority field.

### Step 4 (blocker branch) - Internal comment mentioning the creator
- Operation: `devrev` / `add_comment`.
- `object` = `$get('ticket_created_1', 'output').id`.
- `visibility` = literal `internal` (comments default to **external** - set this
  explicitly or the mention leaks to the customer).
- `body` (text_template) mentions the creator. Use the **variable picker** to insert the
  creator mention so the UI emits the correct token; the raw form is the user id wrapped in
  angle brackets: `'<' + created_by.id + '>'`. The starter template encodes this as:
  `<% expr '<' & $get('ticket_created_1', 'output').created_by.id & '>' %>`. If your
  org's mention token differs, re-insert it via the variable picker.

### Step 5 (other branch) - Different internal comment
- Operation: `devrev` / `add_comment`, `visibility` = `internal`, different body text
  (the starter uses a "no escalation required" message echoing the severity).

### Step 6 - Deploy & test
- Publish only after the trigger part filter is set.
- Create test tickets in the Part 1 Test part: one `blocker`, one non-blocker.
- Verify both runs in the **Runs** tab and the automated comments on each ticket.

## Per-step field mapping (quick reference)

| Node | Field | Type | Value |
|------|-------|------|-------|
| Ticket Created | (trigger filter) | - | Part = Part 1 Test part |
| If/Else | condition | literal | nested group, `contains_any` `["blocker"]` on `.severity` |
| Update Ticket (blocker) | id | jsonata | `$get('ticket_created_1','output').id` |
| Update Ticket (blocker) | priority | **real exposed field** | choose in sandbox - NOT priority_v2 |
| Add Comment (blocker) | object | jsonata | `$get('ticket_created_1','output').id` |
| Add Comment (blocker) | visibility | literal | `internal` |
| Add Comment (blocker) | body | text_template | creator mention `<created_by.id>` via picker |
| Add Comment (other) | object | jsonata | `$get('ticket_created_1','output').id` |
| Add Comment (other) | visibility | literal | `internal` |
| Add Comment (other) | body | text_template | different message |

## Test matrix

| # | Input ticket | Expected branch | Expected result |
|---|--------------|-----------------|-----------------|
| 1 | severity = blocker | true | priority updated + internal comment mentioning creator |
| 2 | severity = high | false | different internal comment, no priority change |
| 3 | severity = low | false | different internal comment, no priority change |
| 4 | ticket in a *different* part | (no trigger) | workflow does not run (filter proof) |
