"""Part 3 - build a SAFE works.create request body (Execute Code node, BEFORE the HTTP node).

Trigger: ticket created with severity 'low' (filter + dedicated part).
This module builds the JSON string for POST https://api.devrev.ai/works.create (the
exercise's 'work.create' is a typo; the real endpoint is 'works.create').

Design notes / preflight bounds:
- Uses json.dumps to build the body safely (no manual string concatenation / injection).
- Validates inputs BEFORE building: ticket title is required, trimmed, and bounded to
  <= 256 chars (a stated design assumption - DevRev does not publish an exact title cap, so
  256 is a conservative preflight guard the caller can raise). owned_by must be a NON-EMPTY
  list of non-empty string DONs; applies_to_part must be a non-empty string.
- Adds external_ref 'devrevu-p3:<ticket id>' to MITIGATE duplicate creation. This does NOT
  guarantee exactly-once; see duplicate_policy.py + the response validator + guide for the
  "lookup-before-create / handle 409 conflict" discussion. Do NOT blindly POST-retry.
- OPTIONAL scope check: if the caller passes expected_org_id, we assert the provided owner /
  part DONs are consistent with it ONLY as a sanity check. We NEVER fabricate an org id and
  there is NO default - DON scoping is validated EXTERNALLY in the sandbox; this is a best-
  effort guard, not an authority on org membership.
- All example values here are SYNTHETIC placeholders. Bind real trigger fields in the node.

Execute Code signature (current docs): def run(inputs, keyrings) -> dict.
"""

import json

# Conservative preflight title bound (design assumption, not a published API limit).
MAX_TITLE_LEN = 256

# The ONLY endpoint this workflow may POST to. The HTTP node URL must be exactly this fixed,
# HTTPS DevRev endpoint. We validate it in code so a copy/paste typo, an http:// downgrade,
# or an attacker-controlled host cannot be used (and so Part 5's fault injection, which uses
# a WRONG path, is caught here too).
WORKS_CREATE_URL = "https://api.devrev.ai/works.create"
_ALLOWED_HOSTS = ("api.devrev.ai",)


def _nonempty_str(v):
    return isinstance(v, str) and v.strip() != ""


def validate_endpoint(url):
    """Validate the HTTP node URL. Returns the normalized URL or raises ValueError.

    Enforces: HTTPS scheme only, an allow-listed DevRev host, and the works.create path.
    No credentials, query strings, or alternate hosts are permitted.
    """
    if not _nonempty_str(url):
        raise ValueError("endpoint URL is required")
    u = url.strip()
    if not u.startswith("https://"):
        raise ValueError("endpoint must use HTTPS (http:// and other schemes are rejected)")
    # Parse host without pulling in urllib for such a small, fixed check.
    rest = u[len("https://"):]
    host = rest.split("/", 1)[0].split("?", 1)[0].split("@")[-1].split(":")[0].lower()
    if host not in _ALLOWED_HOSTS:
        raise ValueError("endpoint host is not an allow-listed DevRev host")
    if u != WORKS_CREATE_URL:
        raise ValueError(
            "endpoint must be exactly %s (no alternate path/query/credentials)" % WORKS_CREATE_URL
        )
    return u


def _check_owner_ids(owned_by_ids):
    if not isinstance(owned_by_ids, (list, tuple)) or len(owned_by_ids) == 0:
        raise ValueError("owned_by_ids must be a non-empty list of user DONs")
    cleaned = []
    for owner in owned_by_ids:
        if not _nonempty_str(owner):
            raise ValueError("every owner id must be a non-empty string DON")
        cleaned.append(owner.strip())
    return cleaned


def build_works_create_body(
    ticket_id,
    title,
    applies_to_part_id,
    owned_by_ids,
    severity,
    expected_org_id=None,
):
    """Pure, testable core. Returns (body_str, external_ref). Raises ValueError on bad input.

    Args:
      ticket_id: trigger ticket id (used only to derive external_ref; not sent as a field).
      title: issue title (from ticket title). Required, trimmed, <= MAX_TITLE_LEN.
      applies_to_part_id: part the issue applies to (non-empty string DON).
      owned_by_ids: NON-EMPTY list of non-empty user DON strings.
      severity: ticket severity string (for logging/body text only).
      expected_org_id: OPTIONAL caller-provided sandbox org identifier. If provided, each
        provided DON that contains an org segment is sanity-checked to contain it. No default;
        never fabricated. External validation remains the source of truth.
    """
    if not _nonempty_str(title):
        raise ValueError("title is required and must be a non-empty string")
    normalized_title = title.strip()
    if len(normalized_title) > MAX_TITLE_LEN:
        raise ValueError("title exceeds the maximum of %d characters" % MAX_TITLE_LEN)
    if not _nonempty_str(applies_to_part_id):
        raise ValueError("applies_to_part_id is required and must be a non-empty string")
    owners = _check_owner_ids(owned_by_ids)
    part = applies_to_part_id.strip()

    if expected_org_id is not None:
        if not _nonempty_str(expected_org_id):
            raise ValueError(
                "expected_org_id, when provided, must be a non-empty string (no default)"
            )
        org = expected_org_id.strip()
        # Best-effort sanity check ONLY. We do not fabricate or infer org ids; external
        # validation in the sandbox is authoritative. Only checks DONs that look scoped.
        for don in [part] + owners:
            if don.startswith("don:") and (org not in don):
                raise ValueError(
                    "a provided DON is not consistent with expected_org_id "
                    "(external validation is authoritative; adjust or omit expected_org_id)"
                )

    external_ref = "devrevu-p3:" + str(ticket_id)

    payload = {
        "type": "issue",
        "title": normalized_title,
        "applies_to_part": part,
        "owned_by": owners,
        # Synthetic, non-sensitive reference body. Replace/augment in the node as needed.
        "body": (
            "Auto-created from DevRevU Part 3 workflow for a 'low' severity ticket "
            "(synthetic reference)."
        ),
        # Duplicate-mitigation idempotency hint; not an exactly-once guarantee.
        "external_ref": external_ref,
    }
    return json.dumps(payload, separators=(",", ":")), external_ref


def run(inputs, keyrings):
    """Execute Code entrypoint. Configure node inputs:
      ticket_id, title, applies_to_part_id, owned_by_ids (list), severity,
      and OPTIONALLY expected_org_id (caller-provided; no default) and endpoint (the HTTP
      node URL - validated against the fixed HTTPS works.create endpoint when provided).
    Configure node outputs: body (text), external_ref (text), endpoint (text).
    """
    inputs = inputs or {}
    endpoint = validate_endpoint(inputs.get("endpoint", WORKS_CREATE_URL))
    body, external_ref = build_works_create_body(
        ticket_id=inputs.get("ticket_id", ""),
        title=inputs.get("title"),
        applies_to_part_id=inputs.get("applies_to_part_id"),
        owned_by_ids=inputs.get("owned_by_ids"),
        severity=inputs.get("severity", ""),
        expected_org_id=inputs.get("expected_org_id"),
    )
    return {"body": body, "external_ref": external_ref, "endpoint": endpoint}
