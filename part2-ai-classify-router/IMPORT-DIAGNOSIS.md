# Part 2 import diagnosis

> **RESOLUTION (code-format repair) - proven root cause found.** A REAL Execute Code export
> sample from this org (kept OUTSIDE the repo at the workdir root,
> `15-Part 2 - validation issue-template-2.json`) shows an `invoke_code` node importing fine,
> with its `code` input configured as **`{"type": "text_template", ...}`** - NOT
> `{"type": "literal", ...}`. The earlier Execute Code edition used `literal` for both `code`
> fields; that value-type mismatch is the proven delta. `templates/11-Part 2-template.json`
> has been restored to the **full Execute Code edition** (title `Part 2 - Code validation`,
> 18 steps, both Code validators intact) with **both `code` fields flipped to
> `text_template`**. Status: **Repair prepared - import / re-export validation PENDING** (NOT
> a proven live pass).
>
> **What the sample does NOT confirm (do not over-claim):** the sample's Code node is bare -
> it carries ONLY the `code` field, with **no `input_values` and no `output_schema`**. So the
> `input_values` (mapped Code inputs) and `output_schema` (typed Code outputs) shapes kept in
> our template are the **available reference-docs candidate**, not confirmed by this export.
> They remain in the template because the downstream Router/If-Else/comments consume typed
> Code outputs; if a live import strips them, re-map outputs in the sandbox. The sample's
> Add Comment used a hardcoded ticket DON - that was intentionally **NOT** copied here; our
> comments target the trigger ticket dynamically via `$get('ticket_created_1','output').id`.
>
> **Regression guard added:** `code/check_import_roundtrip.py` now compares the VALUE TYPE of
> every input field (not just the code body), so a future `literal` <-> `text_template` flip
> on the `code` field is flagged `[VALUE TYPE CHANGED]`. `code/test_part2_template.py` asserts
> both `code` fields are `text_template`.
>
> An optional diagnostic probe, `Part2-code-compatibility-probe.json` (workdir root), preserves
> the exact bare-sample Code-node shape (trivial `def run(inputs, keyrings): return {}`, no
> outputs) with a dynamic, DON-free Add Comment - import it first to confirm the bare Code
> import shape before the full template.
>
> The diagnosis BELOW is retained as the HISTORICAL record of the earlier failed import. The
> old literal-code template is archived at
> `templates/archive/11-Part 2-code-validation.UNVERIFIED.json` (do not import), and the
> round-trip diagnostic still reproduces against the historical EXPECTED template
> (`Part2-corrected-template.json`, workdir root) vs the failed export (`14-Part 2-template.json`).

> **(HISTORICAL) IMPORT VALIDATION FAILED for the Execute Code edition - do not publish it.**
> These are LOCAL structural checks only; they do NOT simulate the DevRev importer and are
> NOT proof of live import compatibility.

## What was compared

A real workflow template **exported after an import attempt** was compared against the
**expected** Part 2 template using the standard-library checker
[`code/check_import_roundtrip.py`](code/check_import_roundtrip.py). The checker decodes the
export wrapper (`{"data": "<stringified inner JSON>", "templateVersion": "..."}`), then
compares the two graphs semantically: reference keys, operation signatures (including the
embedded Execute Code body), edges, and `$get(...)` references in jsonata, text templates,
and router/if_else conditions. It ignores step/key ordering, canvas positions, and prose
descriptions.

## Result: the import dropped steps (checker exits 1)

Steps present in the expected template but **missing from the exported-after-import**
template (exact reference keys):

- `validate_classification` (Execute Code / `invoke_code`)
- `bug_validate_title` (Execute Code / `invoke_code`)
- `bug_justification_comment` (`add_comment`)
- `feature_justification_comment` (`add_comment`)
- `enhancement_justification_comment` (`add_comment`)

Consequences the checker also flags:

- **10 edges removed** - every connection into or out of those dropped steps, including
  `ask_ai_1 -> validate_classification`, `validate_classification -> router_1`,
  `bug_set_severity -> bug_validate_title`, and the three severity/retain paths that fed the
  per-route justification comments.
- **Dangling references** - the surviving Router route conditions and comment bodies still
  reference `$get('validate_classification', 'output')`, and the Bug title If/Else and
  invalid-title comment still reference `$get('bug_validate_title', 'output')`. Those targets
  no longer exist in the exported graph.

This is concrete evidence that the import changed the graph. It is **not** evidence that the
wrong file was imported, and it does **not** establish *why* the importer dropped the steps.

## What is NOT established

The root cause is unverified. The exact supported Execute Code (`invoke_code`)
operation/configuration/output export shape for this org has not been confirmed from a real
saved sample. A local JSON/graph/Python check cannot reproduce the DevRev importer's behavior.

## Required next sample (synthetic, sandbox only)

Build a tiny, separate draft in the test sandbox: **Ticket Created -> Execute Code ->
Add Comment**. Configure the Code step with a mapped title input, a declared text output
(e.g. `checked_title`), and a trivial `def run(inputs, keyrings): ...` body; explicitly save
the Code configuration. Map Add Comment to the triggering ticket, internal visibility, and
insert the Code output through the variable picker. Export the saved workflow.

That export yields the **actual** `invoke_code` operation/config/output shape and a real
downstream reference. Repair the Part 2 template against it, re-import and re-export, then run:

```bash
python3 code/check_import_roundtrip.py EXPECTED.json FRESH_EXPORT_AFTER_IMPORT.json
```

Only publish once that check reports `PASS`. Even then, PASS means the two files describe the
same graph locally; a live sandbox import/run is still required for compatibility proof.

## Reproduce the check

```bash
# From the repo root; the real export sample and the written report are kept OUTSIDE the repo
# (at the workdir root) so the repo stays public-safe and the original export is unchanged.
python3 part2-ai-classify-router/code/check_import_roundtrip.py \
  <expected-template.json> <exported-after-import.json> \
  --report <out.json>
# exit 0 = round-trip preserved; exit 1 = import changed the graph (expected here).
```

The checker's own behavior is covered by synthetic unit tests in
[`code/test_import_roundtrip.py`](code/test_import_roundtrip.py) (reorder passes; drops,
dangling refs, wrong target/port, changed slug/fields/code, and duplicate keys all detected).
No internal documents or private files were copied into this repository.
