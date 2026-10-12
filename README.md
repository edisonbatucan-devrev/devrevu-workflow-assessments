# DevRevU Workflow Assessment

This repo holds the work for the DevRevU "Advanced Workflow Exercise" (Parts 1-5): each part
builds a different piece of DevRev automation, from simple severity branching up to a snap-in
and a monitoring/debug exercise. All live work was done in the sandbox org
[`edison-org-for-test`](https://app.devrev.ai/edison-org-for-test).

Start with the **View evidence** link for any part below to see the screenshots and notes for
that part. Each part also has a short setup guide if you want to rebuild it yourself.

## The parts

| Part | What it does | Evidence |
|------|--------------|----------|
| 1 - Severity branching | On a new ticket, branches on severity and posts the right internal comment on each path. | [View evidence](part1-ticket-severity-branch/screenshots/CHECKLIST.md) · [setup guide](part1-ticket-severity-branch/BUILD-GUIDE.md) |
| 2 - AI classify + Router | On a new ticket, Ask AI classifies it, then a Router sends it down a Bug / Feature / Enhancement path and sets severity and comments. | [View evidence](part2-ai-classify-router/checklist.md) · [setup guide](part2-ai-classify-router/build.md) |
| 3 - HTTP works.create | On a low-severity ticket, calls `works.create` over HTTP to open an issue, reverses the severity, comments on both, and notifies the owner. | [View evidence](part3-http-work-create/checklist.md) · [setup guide](part3-http-work-create/build.md) |
| 4 - Business Hours snap-in | A custom operation that checks a timestamp against a schedule and returns whether it is within business hours. | [View evidence](part4-business-hours-snapin/screenshots/CHECKLIST.md) · [setup guide](part4-business-hours-snapin/BUILD-GUIDE.md) |
| 5 - Monitoring / debug | Rejects a controlled fault and accepts valid input once the fault is removed. | [View evidence](part5-monitoring-debug/screenshots/CHECKLIST.md) · [setup guide](part5-monitoring-debug/BUILD-GUIDE.md) |

## How to read the evidence

**Parts 1-3** were built and run in the sandbox org, and their evidence pages show real
screenshots of the workflows in DevRev. **Parts 4-5** were verified with local tests that use
mocked or synthetic input: those tests passing shows the code logic works, but they are not
proof of a deployed snap-in, a live workflow run, or an AI-generated explanation in the UI.

There is no official DevRevU LMS pass or score recorded here, because none was provided.
