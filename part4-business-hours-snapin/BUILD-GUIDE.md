# Part 4 - Local Business Hours Validator test

## Goal and scope

Check that the custom operation handles within-hours, outside-hours, and error cases on your Mac.

**Local verification passed. Terminal screenshots still need to be added.**

This is the local-only scope selected by Edison. Tests use mocked schedule responses and a fake HTTP transport. They make no live DevRev API calls and send no messages.

A local test does not prove that a snap-in is installed or that a workflow ran in DevRev. The original Workflow Builder screenshots are not included in this local evidence.

## What it does

The operation takes `org_schedule_id` and `timestamp` and returns:

- `is_within_business_hours`: Whether the supplied schedule response says the timestamp is within hours.
- `next_open_time`: A next opening checked against the supplied responses, or empty if none is verified.
- `evaluated_at`: The normalized timestamp.

Within hours, the next opening is empty. Outside hours, the code follows the schedule's transitions and checks for an opening. Invalid input or an unavailable schedule returns an error, not a guessed offline result.

## Run the local checks

From `part4-business-hours-snapin/code`:

```bash
npm run build
npm run test:core
npm run test:adapter
npm run test:core-py
```

These are the commands to capture for the evidence. No DevRev login, PAT, real schedule, channel, or workflow is needed.

On a fresh checkout, install the locked dependencies first:

```bash
npm ci --ignore-scripts
```

Dependency installation may need internet access. The test runs themselves use local fixtures only.

## Verified results

- TypeScript build: Passed.
- Node core tests: 18 passed.
- Compiled SDK adapter and function-registration tests: 12 passed.
- Python parity tests: 17 passed.

The adapter tests use the installed DevRev SDK v1.1.79 with an injected fake `fetch`. They check request construction, outputs, function dispatch, and safe errors. They do not check a real server response or deployment.

## Add your screenshots

Use `screenshots/CHECKLIST.md` for short image placeholders and captions.

Capture the build, within-hours case, outside-hours case, adapter tests, and error cases. Label these as local mocked tests. Do not add screenshots of an active workflow unless that workflow was actually built and run.

Keep credentials, browser authorization URLs, and private data out of evidence.

## Optional packaging

```bash
npm run package
```

This creates `build.tar.gz`. Packaging is not installation and is not required to demonstrate the local test results.

The package exports its function through `dist/index.js` and `functionFactory`. Generated output, dependencies, and archives are ignored by Git.

## Sandbox integration - separate and not verified

The original exercise includes a custom node in Workflow Builder, its input panel, an active Conversation Created workflow, and within-/outside-hours runs. Those remain separate from the chosen local proof.

The manifest previously passed server-side validation. That was a remote check, not an offline test. Version creation did not return a successful receipt, and the follow-up lookup showed no version. No installation or live workflow run is claimed.

Do not retry package/version creation for this local task. If sandbox integration is resumed later, inspect the existing package first rather than creating another one.

`workflow.build-spec.json` describes the intended integration; it is not an importable workflow or proof that it ran.
