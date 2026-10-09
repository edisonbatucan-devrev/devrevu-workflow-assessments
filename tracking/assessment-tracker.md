# DevRevU - Workflows and Automations assessment tracking

Repository: https://github.com/edisonbatucan-devrev/devrevu-workflow-assessments
Sandbox: https://app.devrev.ai/edison-org-for-test

This tracker reflects only what is prepared and locally verifiable in this repository. It is
not an official DevRevU LMS pass/score and does not independently certify every acceptance
criterion. See `assessments.json` for the machine-readable version and `test-execution-report.md`
for exact commands and results.

## Part 1 - Workflow fundamentals  -  Completed (confirmed by Edison, 2026-10-08)

- [x] Build the severity-branching workflow (Edison-confirmed complete).
- [x] Screenshots included in the repository.

Completion is recorded from Edison's explicit confirmation. The importable draft starter is
`../part1-ticket-severity-branch/templates/10-Part 1-template.json` (the comment bodies use the
documented `{% expr ... %}` markers).

### Current evidence (re-described from the actual screenshot content)
- `image.png`: Workflow "Part 1" canvas, version **v1** marked Current and Active. Ticket
  Created -> Control "Severity is blocker?" -> True "Blocker internal comment" / False
  "Non-blocker internal comment". No separate priority-update action is visible on the canvas.
- `image-1.png`: Runs tab + Run Details for **WORKFLOW-10 on v1 for TKT-11**, status
  **Completed**; the True (blocker) branch executed with success checkmarks.
- `image-2.png`: **TKT-11** (Severity Medium) with an internal workflow comment whose creator
  mention renders as a resolved `@edison-batucan` (not a literal expression).

> Earlier tracking described a Medium ticket **TKT-9** on a **v2** version with a literally
> rendered expression, plus a fourth screenshot `image-3.png`. Those notes describe a *prior*
> capture and are retained only as historical observations in `assessments.json`. They are not
> re-associated to the current same-name screenshots, and `image-3.png` is not present.

### Historical observation - comment rendering fix
A prior capture rendered the comment expression literally. The exported text templates had used
`<% expr ... %>` instead of the documented `{% expr ... %}`; both comment bodies were corrected
in the template. The current screenshots (TKT-11, v1) do not show that symptom. This is a
historical note, not a claim about the live runtime now.

### Optional acceptance checklist (does not reopen completion)
- Trigger filtered to a dedicated test part before publishing - pending live proof.
- Blocker branch updates a REAL exposed priority field (not `priority_v2`) - pending.
- Blocker-branch creator mention via dynamic variable - evidenced (image-2.png).
- Non-blocker branch posts a different comment - prepared (branch exists; no ticket screenshot).
- Published and Active + successful run in Runs tab - evidenced (image.png, image-1.png).

### Part 1 priority-field gap (explicit)
The exercise requires a **priority field update** on the blocker branch; it is NOT satisfied by
substituting severity. The importable starter `10-Part 1-template.json` deliberately **omits**
the priority-update step (no verified exposed priority field), so this requirement is
**not verified** - it must be added in the sandbox against a real priority field. Part 1 is
recorded complete only on Edison's explicit confirmation; the priority sub-requirement remains
`manual-pending`.

## Part 2 - AI classification + Router  -  DIRECT candidate; local checks only, live import PENDING

The current candidate is the **direct Ask AI -> Router** template, with no Execute Code steps:

- Template: `../part2-ai-classify-router/templates/11-Part 2-direct-router.template.json` (title
  **`Part 2 - Direct AI Router (regex validation)`**). Flow:
  `Ticket Created -> Ask AI -> Router (EXACTLY 3 routes)`.
- Ask AI returns two lines (a category line + a `Justification:` line). The Router has **exactly
  3 named routes** (Bug/Feature/Enhancement), each matched by a JSONata `$match` regex on the AI
  output. Bug -> severity high + a native `if_else` JSONata `$match` regex title check
  (`^\[BUG\] .{5,120}$`) + internal invalid-title comment. Feature/Enhancement -> severity
  medium. Internal classification-justification comment on each accepted path.
- Malformed AI output matches no route and performs no branch action - a Completed run with no
  route taken is **not** success; inspect the actual AI output and route in the Runs tab.
- All comments internal; all object/id targeting is dynamic
  `$get('ticket_created_1','output').id` (no hardcoded DON). Bug title format is a stated lab
  convention, not an assessment requirement.
- **NOT verified:** a LIVE sandbox import, dynamic Router port behavior, and JSONata `$match`
  evaluation inside Router/if_else conditions. Confirm with the builder's Validate action.
- **Status:** **CANDIDATE - import/execution UNVERIFIED.** Locally structure-validated only
  (`../tests/part2/test_direct_router_template.py`: Ask AI wired directly to Router, exactly 3
  routes with matching ports, no `invoke_code`/validator references, reachable/acyclic, no
  dangling `$get`, Bug=high and the other two `update_ticket` steps=medium, severity enum
  lowercase, single `if_else` with true/false ports, internal comments, no hardcoded DON, plus
  Python equivalents of the routing/Bug-title regex samples). REQUIRED before publish: filter the
  trigger to a dedicated Part 2 sandbox test part. **Do NOT publish** unless the live import +
  Validate succeed. Build/verify notes: `../part2-ai-classify-router/build.md`.
- The shared `../tools/check_import_roundtrip.py` + its synthetic unittests
  (`../tests/test_import_roundtrip.py`) remain in the passing local suite; after a live import,
  re-export and run the checker (candidate vs re-export) - it must PASS.

## Parts 3-5 - Prepared, sandbox build / live validation pending

Each part ships runnable local artifacts (code + tests or a clearly-labeled build map/spec).
Nothing in Parts 3-5 has been deployed or live-run; reviewer and run links are null.
- **Part 3 - HTTP works.create + reverse severity**: request builder, response validator,
  severity reverse, duplicate/notify policy, all unit-tested (`../tests/part3/test_part3.py`);
  build map `../part3-http-work-create/build.json`, narrative
  `../part3-http-work-create/build.md`. The real `works.create` response field path must be
  captured live (no committed sample). Build / live-test / evidence: pending.
- **Part 4 - Business Hours Validator snap-in**: dependency-free core (`.mjs` + `.ts` twins) with
  a Python semantic-parity twin that is actually executed here; candidate manifest and SDK
  adapter marked explicitly as not compiled/CLI-validated. Build / live-test / evidence: pending.
- **Part 5 - Monitoring & debugging**: fault-injection build-spec plus Python tests proving the
  Part 3 validator raises on the injected fault and recovers on a fixed synthetic response.
  Live debug / fix / evidence: pending.
