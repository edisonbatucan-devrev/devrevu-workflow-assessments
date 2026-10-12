# Local test results

Latest check: October 12, 2026. These results describe local tests, not a deployment or a DevRevU score.

## Part 4 - chosen local proof

**Local verification passed. Screenshots still need to be added.**

Run from `part4-business-hours-snapin/code`:

```bash
npm run build
npm run test:core
npm run test:adapter
npm run test:core-py
```

| Check | Result |
| --- | --- |
| TypeScript build | Passed |
| Node core cases | 18 passed |
| SDK adapter and function-registration cases | 12 passed |
| Python parity cases | 17 passed |

The schedule responses and HTTP transport are mocked. These checks show compilation, within-/outside-hours logic, input/output handling, function dispatch, and safe error behavior. They do not show an installed snap-in, a real schedule response, or a live workflow.

Add terminal screenshots using `part4-business-hours-snapin/screenshots/CHECKLIST.md`.

Earlier CLI manifest validation returned `Manifest is valid`; that was a remote check and is not part of the offline proof. No successful version receipt, sandbox installation, or live workflow run is claimed.

## Repository-wide runner

```bash
python3 run_tests.py
```

Latest result: **not fully passing**.

- Python suites: 127 tests ran; 2 failed.
- Project JSON validation: Passed (10 files).
- Reference paths: Passed.
- Node core check: Passed.

The failing checks are:

- Part 2: `test_only_one_if_else_with_true_false_ports`.
- Part 3: `test_committed_file_matches_generator`.

These export-structure/generator checks need review against the updated Part 2 and Part 3 files. Their workflows and evidence were not changed during this Part 4 documentation update. Edison has separately confirmed Parts 2 and 3 completed.

The JSON scan now excludes installed dependencies and generated output. Third-party JSONC files in `node_modules` are not treated as project evidence.

## Scope notes

- Part 4 is locally verified for the user-selected mocked-test scope.
- Screenshots are still placeholders until Edison adds them.
- Original hosted Workflow Builder evidence remains separate and unverified.
- Part 5 failure/recovery evidence is not claimed complete here.
- No official LMS pass, certification score, or deployment approval is inferred.
