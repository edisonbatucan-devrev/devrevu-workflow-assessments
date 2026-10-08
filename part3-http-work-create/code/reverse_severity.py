"""Part 3 - reverse the ticket severity string (Execute Code node).

Reverses a validated severity string (e.g. 'low' -> 'wol') to be added as a comment on the
created issue. Validates against the known lowercase enum first so garbage is rejected.
"""

VALID_SEVERITIES = ("low", "high", "medium", "blocker")


def reverse_severity(severity):
    """Pure, testable core. Returns {reversed, original}. Raises ValueError if invalid."""
    if not isinstance(severity, str):
        raise ValueError("severity must be a string")
    normalized = severity.strip().lower()
    if normalized not in VALID_SEVERITIES:
        raise ValueError(
            "severity must be one of %s" % ", ".join(VALID_SEVERITIES)
        )
    return {"reversed": normalized[::-1], "original": normalized}


def run(inputs, keyrings):
    """Execute Code entrypoint. Input: severity (text). Outputs: reversed (text),
    original (text)."""
    inputs = inputs or {}
    return reverse_severity(inputs.get("severity"))
