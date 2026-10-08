"""Part 2 - Bug title-format validator (Execute Code node body).

Runs inside a DevRev `invoke_code` (Execute Code) node on the Bug path. It validates the
proposed lab title against a format and returns a structured result the workflow can branch
on and quote in a comment.

ASSUMPTION (documented): the exercise does NOT specify a required Bug title format. We
therefore ASSUME the convention `[BUG] <5-120 chars>`, i.e. regex `^\\[BUG\\] .{5,120}$`.
This is a deliberate, stated assumption - adjust the pattern in the sandbox if the grader
expects a different format.

DevRev Execute Code (Python) signature (current docs): `def run(inputs, keyrings)`.
Return a dict and explicitly configure the node outputs to match the returned keys.
No AI determinism is assumed anywhere; malformed/empty input is handled safely.
"""

import re

# Assumed Bug title format. Stated assumption - exercise does not define one.
BUG_TITLE_PATTERN = r"^\[BUG\] .{5,120}$"
_BUG_TITLE_RE = re.compile(BUG_TITLE_PATTERN)


def validate_bug_title(title):
    """Pure, testable core. Returns a dict with validation outcome.

    Keys:
      is_valid (bool), reason (str), normalized_title (str), pattern (str)
    """
    if not isinstance(title, str):
        return {
            "is_valid": False,
            "reason": "Title was missing or not a string.",
            "normalized_title": "",
            "pattern": BUG_TITLE_PATTERN,
        }
    normalized = title.strip()
    if not normalized:
        return {
            "is_valid": False,
            "reason": "Title was empty after trimming whitespace.",
            "normalized_title": "",
            "pattern": BUG_TITLE_PATTERN,
        }
    is_valid = _BUG_TITLE_RE.match(normalized) is not None
    reason = (
        "Title matches the assumed Bug format."
        if is_valid
        else "Title does not match the assumed Bug format '[BUG] <5-120 chars>'."
    )
    return {
        "is_valid": is_valid,
        "reason": reason,
        "normalized_title": normalized,
        "pattern": BUG_TITLE_PATTERN,
    }


def run(inputs, keyrings):
    """DevRev Execute Code entrypoint.

    Expected inputs (configure the node's input list accordingly):
      - title: the proposed lab/ticket title (text)
    Configure outputs: is_valid (bool), reason (text), normalized_title (text),
    pattern (text).
    """
    inputs = inputs or {}
    result = validate_bug_title(inputs.get("title"))
    return result
