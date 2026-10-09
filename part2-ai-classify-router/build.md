# Part 2 - AI classification + Router (direct, regex title validation)

**Candidate (unverified):** `templates/11-Part 2-direct-router.template.json`.
Flow: **Ticket Created -> Ask AI -> Router (Bug / Feature / Enhancement)**, no Execute Code
steps. Bug -> severity High + regex title check + internal invalid-title comment; Feature /
Enhancement -> severity Medium; an internal classification-justification comment on every
accepted path. Org: `edison-org-for-test`, trigger filtered to a dedicated Part 2 test part.

> **Status:** locally graph-validated only (`tests/part2/test_direct_router_template.py`).
> A live DevRev import, dynamic Router ports, and JSONata `$match` regex evaluation are
> **UNVERIFIED** - nothing here claims the template imports or runs. Do **not** publish until
> you import it, confirm the Ask AI -> Router connection and three named ports, and set the
> trigger part filter.

## Flow

- **Ticket Created** -> **Ask AI** -> **Router** with exactly three named routes.
- **Bug** -> set severity `high` -> regex title check (`^\[BUG\] .{5,120}$`) -> internal
  invalid-title comment when the title does not match -> internal classification-justification
  comment.
- **Feature** -> set severity `medium` -> internal classification-justification comment.
- **Enhancement** -> set severity `medium` -> internal classification-justification comment.

All comments are `internal`. Every object/id target is dynamic
(`$get('ticket_created_1','output').id`); no hardcoded DON ids.

## Ask AI prompt (embedded in the template)

The Ask AI node's `ai_input` is a two-line contract that treats the ticket text as untrusted
DATA (the exact string lives in the template):

```
Classify the ticket as exactly one of Bug, Feature, Enhancement.
...
Return exactly TWO lines, no JSON, Markdown, fences, or extra text:
Bug
Justification: A brief factual reason.
```

The ticket title and body are delimited in `<ticket_title>` / `<ticket_body>` tags so embedded
instructions are ignored. Each Router route matches a full, category-specific response with a
JSONata `$match` regex, e.g. `^Bug\r?\nJustification: [^\r\n]{1,1000}\r?\n?$`. Malformed AI
output matches no route and performs no branch action - a Completed run with no route taken is
**not** assessment success; inspect the actual AI output and the route taken in the Runs tab.

Title format `[BUG] ` + 5-120 characters is a stated lab convention, not an assessment
requirement; adjust in the sandbox if the grader expects otherwise.

## Manual verification

1. Import as a NEW draft in `edison-org-for-test`; leave any existing draft unchanged.
2. Confirm a visible Ask AI -> Router connection and three named Router output paths.
3. Configure a dedicated Part 2 test-part filter on the trigger **before** publishing.
4. Validate. If the `$match` conditions or route connections are rejected, do not publish;
   capture the exact error and the exported draft.
5. If validation succeeds, publish and create separate test tickets:
   - Bug / invalid title: title `Login crashes`, body `Existing sign-in crashes after
     submitting valid credentials.` Expect High severity, invalid-title note, justification.
   - Bug / valid title: title `[BUG] Login crashes`, same body. Expect High severity and
     justification, no invalid-title note.
   - Feature: title `New offline mode`, body `Please add offline operation, which the product
     has never supported.` Expect Medium severity and justification.
   - Enhancement: title `Improve existing search sorting`, body `Existing search works; add
     sorting to make results easier to review.` Expect Medium severity and justification.
6. Inspect the actual AI output, route taken, severity update, and internal comments in the
   Runs tab and ticket Discussions. AI classification is non-deterministic - verify the output,
   not only the run status.
7. Export after import and run the round-trip checker against this candidate
   (`python3 tools/check_import_roundtrip.py "part2-ai-classify-router/templates/11-Part 2-direct-router.template.json" EXPORTED.json`).
   Every step and edge must survive before relying on the template.

## Local checks performed

JSON/version wrapper, reference closure, graph reachability, Ask AI -> Router connectivity, no
`invoke_code` or missing validator references, and Python equivalents of the routing/title
regex samples all pass (`tests/part2/test_direct_router_template.py`). These do **not** execute
DevRev's JSONata runtime or importer; live import, validation, and execution remain unverified.

## Evidence

Save real screenshots in `screenshots/` per `checklist.md` (no fabrication). Record test ticket
display_ids in the checklist; never commit real object ids.
