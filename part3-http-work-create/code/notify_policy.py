"""Part 3 - decide the notify/comment step AFTER an issue is confirmed created.

Why this exists (separation of create vs. notify failures):
- The owner notification ("{{ISS-ID}} has been created for your ticket.") and the
  reversed-severity comment on the issue must happen ONLY after the issue is confirmed
  created (validate_response returned work_id + display_id).
- If the notification/comment step later fails, that failure MUST NOT cause the workflow to
  re-run the works.create HTTP node and create a DUPLICATE issue. In the Workflow Builder
  this means: the HTTP create node and the notify/comment nodes are on SEPARATE, SEQUENTIAL
  steps, and any retry/error path is scoped to the notify step only - never back to create.
- This module is the small, testable gate that enforces "notify only after a verified
  create" and produces the exact notification text + comment body. It performs NO network
  calls and makes NO exactly-once claim; it only prevents the duplicate-create footgun.

Execute Code signature (current docs): def run(inputs, keyrings) -> dict.
"""


class NotifyGateError(Exception):
    """Raised when a notify/comment is requested before a verified issue create."""


def _nonempty_str(v):
    return isinstance(v, str) and v.strip() != ""


def plan_post_create_actions(create_result, reversed_severity, ticket_owner_id):
    """Pure, testable core.

    Args:
      create_result: the dict returned by validate_works_create ({work_id, display_id}) OR
        None/empty if the create did NOT verify.
      reversed_severity: the reversed severity string for the issue comment (e.g. 'wol').
      ticket_owner_id: the ticket owner to notify (non-empty string).

    Returns a dict describing the two downstream actions to perform:
      { "should_notify": True, "issue_comment": "<text>", "notification": "<text>",
        "work_id": ..., "display_id": ... }

    Raises NotifyGateError if the issue was NOT verified created (so the workflow does not
    notify or comment on a non-existent issue, and does NOT loop back into create).
    """
    if not isinstance(create_result, dict):
        raise NotifyGateError("No verified issue: refusing to notify (would risk a duplicate create).")
    work_id = create_result.get("work_id")
    display_id = create_result.get("display_id")
    if not _nonempty_str(work_id) or not _nonempty_str(display_id):
        raise NotifyGateError("Issue create did not return both work_id and display_id; not notifying.")

    if not _nonempty_str(reversed_severity):
        raise NotifyGateError("Missing reversed severity for the issue comment.")
    if not _nonempty_str(ticket_owner_id):
        raise NotifyGateError("Missing ticket owner id for the notification.")

    # Exact deliverable text. {{ISS-ID}} is resolved to the real display_id here.
    notification = "%s has been created for your ticket." % display_id
    issue_comment = "Reversed ticket severity: %s" % reversed_severity.strip()

    return {
        "should_notify": True,
        "work_id": work_id,
        "display_id": display_id,
        "issue_comment": issue_comment,
        "notification": notification,
    }


def run(inputs, keyrings):
    """Execute Code entrypoint. Configure node inputs:
      create_result (object: {work_id, display_id} from validate_response),
      reversed_severity (text), ticket_owner_id (text).
    Configure outputs: should_notify (bool), work_id (text), display_id (text),
      issue_comment (text), notification (text).
    Raises if the issue was not verified created, so the run fails here WITHOUT re-creating.
    """
    inputs = inputs or {}
    return plan_post_create_actions(
        inputs.get("create_result"),
        inputs.get("reversed_severity"),
        inputs.get("ticket_owner_id"),
    )
