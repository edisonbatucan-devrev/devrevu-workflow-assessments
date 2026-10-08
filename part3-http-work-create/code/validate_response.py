"""Part 3 - validate the HTTP works.create response (Execute Code node, AFTER the HTTP node).

Why this exists: an HTTP node can "finish" even on a non-2xx response, so a bad request
would otherwise look like a successful run. This validator RAISES on non-2xx or on missing
IDs, so the workflow run is correctly marked FAILED when creation did not actually succeed.

Safety:
- Never leaks the full response body or any tokens into errors/logs. Error messages are
  bounded and generic.
- Extracts work.id and work.display_id ONLY. The exact response field path must be
  confirmed against a REAL captured sandbox response and the node outputs configured from
  that (see guide). This module tolerates the common {"work": {...}} shape and a top-level
  shape, but you must verify in the sandbox.
"""

import json


class WorksCreateError(Exception):
    """Raised when works.create did not clearly succeed. Message is safe to surface.

    `code` lets the workflow branch on the failure class without parsing the message:
      - "non_2xx"        : an unexpected non-2xx status.
      - "rate_limited"   : HTTP 429. Do NOT blindly retry in-node; let the run fail so a human
                           / a controlled backoff decides. No exactly-once guarantee is made.
      - "conflict"       : HTTP 409. A matching issue MAY already exist (duplicate external_ref).
                           Reuse an existing issue ONLY after verifying it has the SAME
                           external_ref/source as this ticket (see verify_conflict_is_same_source).
      - "bad_response"   : 2xx but missing/invalid body or ids.
      - "bad_status"     : status missing / non-numeric.
    """

    def __init__(self, message, code="non_2xx"):
        super().__init__(message)
        self.code = code


def _coerce_json(response_body):
    if isinstance(response_body, dict):
        return response_body
    if isinstance(response_body, str) and response_body.strip():
        try:
            return json.loads(response_body)
        except (ValueError, TypeError):
            raise WorksCreateError("Response body was not valid JSON.", code="bad_response")
    raise WorksCreateError("Response body was empty or of an unexpected type.", code="bad_response")


def verify_conflict_is_same_source(response_body, expected_external_ref):
    """For a 409 conflict: decide whether an existing issue is SAFE to reuse.

    Reuse is permitted ONLY if the conflict response exposes an existing work whose
    external_ref EXACTLY equals the external_ref we sent (i.e. the same ticket/source).
    Returns {work_id, display_id} if a safe reuse target is found, else None. Never raises.
    Never claims exactly-once; this only prevents reusing an UNRELATED issue.
    """
    if not isinstance(expected_external_ref, str) or expected_external_ref.strip() == "":
        return None
    try:
        data = _coerce_json(response_body)
    except WorksCreateError:
        return None
    work = data.get("work") if isinstance(data.get("work"), dict) else data
    if not isinstance(work, dict):
        return None
    if work.get("external_ref") != expected_external_ref:
        return None  # different source -> NOT safe to reuse
    work_id = work.get("id")
    display_id = work.get("display_id")
    if not work_id or not display_id:
        return None
    return {"work_id": work_id, "display_id": display_id}


def validate_works_create(status_code, response_body):
    """Pure, testable core. Returns {work_id, display_id} or raises WorksCreateError.

    Does NOT include the raw body or any secret in raised messages. Distinguishes 429
    (rate limited) and 409 (conflict) via WorksCreateError.code so the workflow can branch
    without blind in-node retries.
    """
    try:
        code = int(status_code)
    except (TypeError, ValueError):
        raise WorksCreateError("Missing or non-numeric HTTP status code.", code="bad_status")

    if code == 429:
        raise WorksCreateError(
            "works.create was rate limited (429). Do not blindly retry in-node.",
            code="rate_limited",
        )
    if code == 409:
        raise WorksCreateError(
            "works.create returned a conflict (409); an issue may already exist. "
            "Reuse only after verifying the same external_ref/source.",
            code="conflict",
        )
    if code < 200 or code >= 300:
        # Bounded, non-leaking message. No body, no headers, no token.
        raise WorksCreateError("works.create returned non-2xx status %d." % code, code="non_2xx")

    data = _coerce_json(response_body)

    # Verify the real path in the sandbox. Accept {"work": {...}} or top-level.
    work = data.get("work") if isinstance(data.get("work"), dict) else data
    work_id = work.get("id") if isinstance(work, dict) else None
    display_id = work.get("display_id") if isinstance(work, dict) else None

    if not work_id or not display_id:
        raise WorksCreateError(
            "works.create succeeded (2xx) but response was missing work.id or work.display_id.",
            code="bad_response",
        )

    return {"work_id": work_id, "display_id": display_id}


def run(inputs, keyrings):
    """Execute Code entrypoint. Configure node inputs:
      status_code (int/text), response_body (text or object - from the HTTP node output).
    Configure node outputs: work_id (text), display_id (text).
    Raises on failure so the run is marked failed.
    """
    inputs = inputs or {}
    return validate_works_create(
        inputs.get("status_code"), inputs.get("response_body")
    )
