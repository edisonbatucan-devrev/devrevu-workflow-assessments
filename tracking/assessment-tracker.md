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

## Part 2 - AI classification + Router  -  ASSESSMENT-ALIGNED (3 routes); import PENDING

This is a **requirements-alignment correction**, not a claim that the import is fixed. The
template now matches the exercise text literally:

- Template: `../part2-ai-classify-router/templates/11-Part 2-template.json` (title
  **`Part 2 - Code validation (3-route aligned)`**, 13 steps). Flow:
  `Ticket Created -> Ask AI -> Execute Code validator -> Router (EXACTLY 3 routes)`.
- The `validate_classification` Execute Code node runs BEFORE the Router. On a clean, in-enum
  result it emits `route` = the accepted label; on **any** malformed/unknown/empty output it
  **RAISES `ValueError`** (stops the run - shown as failed in the Runs tab). **No 4th Review
  route** and **no silent mutation** on bad AI output.
- Router has **exactly 3 named routes** (Bug/Feature/Enhancement) matching the validator enum.
  Bug -> severity high + `bug_validate_title` Code node + internal invalid-title comment.
  Feature/Enhancement -> severity medium **unconditionally** (the earlier no-downgrade gates
  were removed). Classification-justification internal comment on **all 3 paths**.
- **Removed deviations:** the 4th "Review" route, the "AI validator" review branch, and the
  Feature/Enhancement no-downgrade If/Else gates are gone.
- Both `invoke_code` `code` fields are value type **`text_template`** (matches the real export
  sample `../15-Part 2 - validation issue-template-2.json`).
- **NOT verified:** the Code `input_values`/`output_schema` field shapes are the reference-docs
  **candidate**, not confirmed by that bare export; the Ask AI / Router export shapes are not
  independently verified. A LIVE sandbox import + re-export round-trip has **NOT** been run.
- **Status:** **ASSESSMENT CANDIDATE - import still UNVERIFIED.** Locally structure-validated
  (`test_part2_template.py`: exactly 3 routes, validator code raises `ValueError`,
  Feature/Enhancement set medium with no gate, Bug sets high, no dangling `$get`, no cycles,
  internal comments, severity enum, no hardcoded DON; `test_classification_validator.py`:
  strict function returns an enum route and raises on invalid). REQUIRED before publish: filter
  the trigger to a dedicated Part 2 sandbox test part. **Do NOT publish** unless the live import
  + round-trip succeeds and no Code/comments are dropped.
- The pre-repair literal-code edition is archived (do not import) at
  `../part2-ai-classify-router/templates/archive/11-Part 2-code-validation.UNVERIFIED.json`.
  `check_import_roundtrip.py` + its synthetic unittests remain in the passing local suite. See
  `../part2-ai-classify-router/IMPORT-DIAGNOSIS.md` and `BUILD-GUIDE.md`.

## Parts 3-5 - Prepared, sandbox build / live validation pending

Each part ships runnable local artifacts (code + tests or a clearly-labeled build-spec) and a
BUILD-GUIDE. Nothing in Parts 3-5 has been deployed or live-run; reviewer and run links are null.
- **Part 3 - HTTP works.create + reverse severity**: request builder, response validator,
  severity reverse, duplicate/notify policy, all unit-tested; build-spec + synthetic sample
  response. Build / live-test / evidence: pending.
- **Part 4 - Business Hours Validator snap-in**: dependency-free core (`.mjs` + `.ts` twins) with
  a Python semantic-parity twin that is actually executed here; candidate manifest and SDK
  adapter marked explicitly as not compiled/CLI-validated. Build / live-test / evidence: pending.
- **Part 5 - Monitoring & debugging**: fault-injection build-spec plus Python tests proving the
  Part 3 validator raises on the injected fault and recovers on a fixed synthetic response.
  Live debug / fix / evidence: pending.
