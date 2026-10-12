# Part 4 - Workflow evidence

Add your screenshots below. Use ../BUILD-GUIDE.md for setup. Hide tokens and private data.
Capture everything in `edison-org-for-test`.

## What this workflow does

A snap-in node takes a timestamp and tells the workflow if it is within the org's business
hours, plus the next opening time. The Conversation Created workflow then branches: within
hours routes to a live agent, outside hours sends an auto-reply with the next open time.

## 1. Node in the action list

Image: [Add screenshot of the custom node showing up in the Workflow Builder action list]

What it shows: the deployed snap-in node is available to add.

## 2. Node config panel

Image: [Add screenshot of the node's configuration panel with the inputs filled in]

What it shows: the `org_schedule_id` and `timestamp` inputs populated.

## 3. Active workflow

Image: [Add screenshot of the full workflow canvas and its active status]

What it shows: the connected business-hours check, live-agent route, and outside-hours reply.

## 4. Workflow run - within hours

Image: [Add screenshot of a test run that lands within business hours]

What it shows: `is_within_business_hours` true and the conversation routed to the live agent.

## 5. Workflow run - outside hours

Image: [Add screenshot of a test run that lands outside business hours]

What it shows: `is_within_business_hours` false, a verified `next_open_time`, and the
auto-reply with that next opening time.

## Notes

- Org schedule id used (timezone Asia/Manila lab default):
- Live group/agent routed to:
