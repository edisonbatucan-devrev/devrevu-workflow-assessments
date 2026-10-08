# DevRevU - Workflows and Automations assessment tracking

Repository: https://github.com/edisonbatucan-devrev/devrevu-workflow-assessments
Sandbox: https://app.devrev.ai/edison-org-for-test

## Part 1 - Workflow fundamentals

**Status: Completed - confirmed by Edison on October 8, 2026.**

- [x] Complete Part 1 (Edison-confirmed).
- [x] Include screenshots in the repository (present in the inspected revision).

Completion is recorded from Edison's explicit confirmation. It is not an official DevRevU LMS pass/score or independent certification of each acceptance criterion.

### Existing evidence
- `../part1-ticket-severity-branch/screenshots/image.png`: Active v2 workflow canvas.
- `../part1-ticket-severity-branch/screenshots/image-1.png`: Additional canvas screenshot.
- `../part1-ticket-severity-branch/screenshots/image-2.png`: TKT-9 internal workflow comment; the expression appears as literal text.
- `../part1-ticket-severity-branch/screenshots/image-3.png`: Completed workflow executions.

### Non-blocking follow-up - comment rendering fix
- [x] Record Edison's retest: expression still rendered literally with severity set.
- [x] Correct both exported comment expressions from `<% expr ... %>` to `{% expr ... %}` (severity and creator mention).
- [ ] Update both comment bodies in the existing sandbox workflow and publish a new version.
- [ ] Create fresh medium and blocker tickets; confirm actual severity text and clickable creator mention.
- [ ] Add corrected run screenshots, retaining earlier evidence.

Missing severity is no longer the working explanation. A malformed template delimiter was found and corrected locally. Live runtime verification is still pending. Part 1 remains completed as confirmed by Edison; this follow-up does not reopen it.

### Detailed checks retained for reference
Per-item evidence and historical observations remain in `assessments.json`, including the exported template's absent priority-update action and trigger filter. These are optional verification notes, not newly assigned completion blockers. Individual acceptance tests are not marked passed without separate evidence or confirmation.

## Other parts
Parts 2-5 are outside this revision; their completion is not inferred from Part 1.
