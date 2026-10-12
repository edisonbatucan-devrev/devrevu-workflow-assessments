# Part 5 - Local failure and recovery check

## Goal and scope

Use the same local-test approach as Part 4: confirm that a controlled fault is rejected and that valid input is accepted after the fault is removed.

The existing tests reuse Part 3's request and response validators with synthetic data. No API calls, issue creation, notifications, or deployment occur.

**The local tests pass. Screenshots still need to be added.** This is local fault/recovery evidence, not a hosted workflow run or an AI-generated error explanation.

## Run the failure checks

From `part5-monitoring-debug/code`:

```bash
python3 -m unittest test_fault_injection.TestFaultInjectionFails -v
```

The checks cover a rejected typo endpoint, a synthetic non-success response, and an injected exception.

The tests should report `OK`: an expected exception being caught is a successful test. This is not a screenshot of a workflow marked Failed in DevRev.

## Run the recovery checks

```bash
python3 -m unittest test_fault_injection.TestRecoveryAfterFix -v
```

These checks confirm that the correct endpoint is accepted, the synthetic success response is validated, and the normal validator no longer raises.

## Run the complete local set

```bash
python3 -m unittest test_fault_injection -v
```

Expected result: 6 tests pass. A fresh local test run sends no requests and creates nothing.

## Add your screenshots

Use `screenshots/CHECKLIST.md` for the failure-detection, recovery, and full-summary placeholders. Capture the command and the final result. Label the evidence as local tests using synthetic input.

## Original workflow-monitoring evidence - separate

The original bonus exercise also asks for a failed workflow run, failed-node inputs/outputs, the AI error explanation, and a successful run after publishing a fixed version. Local unit tests do not produce or prove those items.

If that integration path is done later, use a copy of Part 3 in `edison-org-for-test`, with notifications disabled. Pause the original test workflow or isolate the copy to a separate test part so both do not process the same ticket.

For a controlled fault, place the temporary exception in the first Code step before the HTTP create step. Do not deliberately fail after creating an issue and then blindly replay creation. Remove the fault, publish the fixed copy, and use a fresh test ticket for recovery.

No active workflow, published-version recovery, AI explanation, or official assessment score is claimed by the local evidence here.
