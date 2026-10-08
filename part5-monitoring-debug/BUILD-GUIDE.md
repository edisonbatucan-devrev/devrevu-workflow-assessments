# Part 5 - Monitoring & debugging (Bonus)

**Goal:** Take a **sandbox COPY** of the Part 3 workflow, intentionally introduce an error,
trigger it, find the failed run in the Runs tab, inspect the failed node's input/output,
read the AI-generated error explanation (the sparkle button), fix it, publish a new
version, and verify success.

**Org:** `edison-org-for-test`. Work on a **copy** so you never disturb a working Part 3.

## Important: make sure the run actually FAILS
An HTTP node can "finish" even on a non-2xx response (e.g. a 404), so a bad endpoint alone
may **not** mark the run as failed. There are two reliable ways to force a genuinely failed
run:

1. **Preferred (deterministic):** keep the Part 3 `validate_response` Execute Code node.
   Point the HTTP node at a wrong path (e.g. `https://api.devrev.ai/works.create-404` or a
   typo). The HTTP node returns a non-2xx; `validate_response` **raises** on non-2xx, which
   marks the run **failed** at that node. This is deterministic and leaks nothing.
2. **Alternative (deterministic raise in code):** leave the endpoint correct but add a
   temporary `raise RuntimeError("Part 5 injected fault")` at the top of the
   `validate_response` node body. This guarantees a failed run without any external call
   dependency.

Do **not** rely on a bare 404 to fail the run; without the validator raise it may show as a
"successful" run with a non-2xx body.

## Fault-injection recipe
See `fault-injection.build-spec.json` for the exact before/after node settings.

## Local proof (non-live)
`code/test_fault_injection.py` proves both halves of this exercise locally without any API
call, reusing Part 3's `validate_response` (it does NOT re-implement comment/notify logic):
- the injected fault (non-2xx 404, or an injected `raise`) makes the validator raise -> the
  run fails; and the deliberate typo endpoint is rejected by the Part 3 endpoint allow-list;
- after the fix, the same validator accepts a synthetic 2xx response and returns the issue
  ids (recovery).

Run it: `cd code && python3 -m unittest test_fault_injection -v`.

## Steps
1. **Duplicate** the Part 3 workflow in the sandbox (new workflow, same steps).
2. Apply fault option 1 or 2 above. Publish this (faulty) version.
3. Trigger it with a low-severity test ticket in the Part 3 test part.
4. Open the **Runs** tab, find the **failed** run.
5. Click into the failed node; inspect **input** and **output** values.
6. Click the **AI error-explanation (sparkle)** button; read the explanation. Screenshot it.
7. **Fix**: restore the correct endpoint (option 1) or remove the injected `raise`
   (option 2).
8. **Publish a new version** and re-trigger.
9. Confirm the new run **succeeds** end to end.

## Screenshot deliverables
See `screenshots/CHECKLIST.md`:
- failed run in Runs tab,
- node error detail with the AI explanation,
- fixed run completing successfully.

## Safety
- All of this is in the sandbox on a copy. Keep the trigger filtered to the Part 3 test
  part. Never point the fault at a real production endpoint or a real token-bearing call
  that could mutate main-org data. Mask any token in screenshots.

## Manual sandbox execution & testing

Done on a **copy** of the deployed Part 3 workflow (so a working Part 3 is never disturbed).
Requires Part 3 already deployed in the sandbox.

- **Prerequisites:** sandbox `edison-org-for-test`; a deployed Part 3 copy; the Part 3 test
  part; the Part 3 `validate_response` Execute Code node retained in the copy.
- **Settings (fault injection, see `build-specs/fault-injection.build-spec.json`):** choose
  option 1 (point the HTTP node at a wrong path, e.g. `.../works.create-404`; the retained
  `validate_response` raises on non-2xx) or option 2 (temporary
  `raise RuntimeError("Part 5 injected fault")` at the top of `validate_response`). Publish
  the faulty version.
- **Trigger / event:** create a **low-severity** test ticket in the Part 3 test part.
- **Expected output (fault):** the run **FAILS** at `validate_response`; open the failed node
  in the Runs tab, inspect input/output, read the AI (sparkle) error explanation.
- **Recovery / expected output (fixed):** restore the correct endpoint (option 1) or remove
  the injected `raise` (option 2); publish a new version; re-trigger; the run **succeeds**
  end to end.
- **Negative / edge note:** a bare 404 alone may show as a "successful" run - rely on the
  `validate_response` raise (option 1) or a deterministic injected raise (option 2) to force
  a genuine failure.
- **Evidence (save in `screenshots/`, see `screenshots/CHECKLIST.md`, mask any token):**
  `failed-run-runs-tab.png`, `node-error-ai-explanation.png`, `fixed-run-success.png`.
  Record the fault option, failed run id and fixed version run id in the checklist.
