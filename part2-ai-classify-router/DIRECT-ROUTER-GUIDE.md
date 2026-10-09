# Part 2 - Direct Ask AI to Router alternative

Template: `templates/11-Part 2-direct-router.template.json`.

This alternative removes the Execute Code steps that prior imports omitted. It is not a claim that those import failures have been diagnosed or fixed. The exercise permits regex-based title validation as an alternative to Execute Code. This version uses standard JSONata `$match` inside native condition expressions; support must be verified by the live builder's Validate action.

## Flow

Ticket Created -> Ask AI -> Router.
- Bug -> severity High -> regex title check -> invalid-title internal comment when needed -> AI classification/justification internal comment.
- Feature -> severity Medium -> AI classification/justification internal comment.
- Enhancement -> severity Medium -> AI classification/justification internal comment.

The prompt requests exactly two lines: a category line and `Justification: ...`. Each route matches a full, category-specific response. Invalid/unexpected output matches no route and therefore makes no branch changes. A Completed run with no route taken is NOT assessment success; inspect the actual AI output and route execution.

There are no references to `validate_classification` or `bug_validate_title`. Title format `[BUG] ` plus 5-120 characters is a stated lab convention, not specified by the assessment.

## Manual verification

1. Import as a NEW draft in edison-org-for-test; leave the existing failed draft unchanged for comparison.
2. Confirm a visible Ask AI -> Router connection and three named Router output paths.
3. Configure a dedicated Part 2 test-part filter before publishing.
4. Validate. If `$match` conditions or route connections are rejected, do not publish; provide the exact error and exported draft.
5. If validation succeeds, publish and create separate test tickets:
   - Bug / invalid title: title `Login crashes`, body `Existing sign-in crashes after submitting valid credentials.` Expect High severity, invalid-title note, and classification justification.
   - Bug / valid title: title `[BUG] Login crashes`, same body. Expect High severity and justification, no invalid-title note.
   - Feature: title `New offline mode`, body `Please add offline operation, which the product has never supported.` Expect Medium severity and justification.
   - Enhancement: title `Improve existing search sorting`, body `Existing search works; add sorting to make results easier to review.` Expect Medium severity and justification.
6. Inspect actual AI output, route taken, severity update and internal comments in Runs and ticket Discussions. AI classification is non-deterministic; verify output, not only run status.
7. Export after import and run the import-comparison checker against this candidate. Every step and edge must survive before relying on the template.

## Checks performed

Local JSON/version, reference closure and graph reachability passed. Python equivalents of sample regex matches passed. These do not execute DevRev's JSONata runtime or importer. Live import/validation/execution remain unverified.

The original Code-based template remains available separately; do not confuse the two editions. No deployment or GitHub push occurs automatically when creating this file.
