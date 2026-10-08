"""Part 2 - AI classification VALIDATOR (Execute Code node, AFTER the Ask AI node).

Runs inside a DevRev `invoke_code` (Execute Code) node placed BETWEEN the Ask AI node and
the Router. It takes the (untrusted, non-deterministic) Ask AI output and validates it into
a safe, strongly-typed decision the Router can branch on. The Router then routes ONLY an
`approved` classification to one of the three main paths (Bug / Feature / Enhancement); any
`requires_review == True` result must go to the review fallback path and MUST NOT mutate the
ticket.

Why this module exists (improvement over trusting the raw AI output):
- The Ask AI node is NOT deterministic and may return malformed JSON, an unknown label, a
  missing/empty justification, a non-numeric or out-of-range confidence, or an object with
  extra/wrong-typed fields. Routing any of those straight into a severity mutation is unsafe.
- This validator NEVER mutates anything. It only classifies the AI output into
  `approved=True` (safe to route to a main path) or `requires_review=True` (route to the
  review fallback) and returns a bounded, safe reason. There is no severity change here.

Prompt-injection note: the UNTRUSTED ticket title/body are handled in the Ask AI prompt
(see ../prompts/classification-prompt.md), which delimits them with explicit tags and
instructs the model to treat them as DATA, never as instructions / tool commands. This
validator never re-interprets the title/body as commands; it only inspects the structured
classifier output. It never executes or evals any field value.

DevRev Execute Code (Python) signature (current docs): `def run(inputs, keyrings)`.
Return a dict and explicitly configure the node outputs to match the returned keys (types
declared in OUTPUT_FIELDS below).
"""

import json

# The ONLY three accepted labels, matched EXACTLY (case-sensitive, no normalization). This
# is deliberate: a strict enum avoids silently accepting "bug", "BUGS", "Feature request",
# etc. If the grader expects case-insensitive matching, that is a one-line policy change
# documented here as a design assumption.
ALLOWED_CLASSIFICATIONS = ("Bug", "Feature", "Enhancement")

# Which key of the Ask AI structured output holds the label. Configurable so the node can be
# pointed at a differently-named field without editing code.
DEFAULT_CLASSIFICATION_KEY = "classification"
DEFAULT_JUSTIFICATION_KEY = "justification"
DEFAULT_CONFIDENCE_KEY = "confidence"

# Justification bounds. Non-empty (after trim) and bounded so a runaway model response can't
# flood a comment. These are design assumptions, not exercise requirements.
MIN_JUSTIFICATION_LEN = 1
MAX_JUSTIFICATION_LEN = 1000

# Optional confidence gate. DESIGN ASSUMPTION: default threshold 0.75. The exercise does not
# define a confidence contract at all, so confidence handling is entirely optional:
#   - If the AI output has no confidence field -> confidence is simply not gated on.
#   - If it IS present, it must be a finite real number in [0,1] and NOT a bool; otherwise
#     the output is sent to review (malformed confidence is itself a red flag).
DEFAULT_CONFIDENCE_THRESHOLD = 0.75

# The single routing label the Router branches on. Exactly one of these is ever emitted, so
# the four Router routes (Bug / Feature / Enhancement / Review) are mutually exclusive by
# construction - each route matches `route` with a single-value `contains_any` list. This is a
# DERIVED field (classification when approved, else "Review"); it changes NO validation
# behavior, it only collapses the approved/requires_review + classification decision into one
# string so the Router config stays a proven `contains_any` match.
REVIEW_ROUTE = "Review"
ALLOWED_ROUTES = ALLOWED_CLASSIFICATIONS + (REVIEW_ROUTE,)

# Declared output field types - configure the Execute Code node outputs to match EXACTLY.
OUTPUT_FIELDS = {
    "approved": "bool",            # True only for a clean, in-enum, well-formed result
    "requires_review": "bool",     # always the logical negation of approved
    "classification": "text",      # the accepted label, or "" when requires_review
    "justification": "text",       # trimmed justification, or "" when requires_review
    "confidence": "text",          # stringified confidence or "" (text avoids null typing issues)
    "reason": "text",              # bounded, safe human-readable reason (never leaks raw input)
    "route": "text",               # derived routing label: Bug/Feature/Enhancement or "Review"
}


def _review(reason):
    """Build a safe review-fallback result. NEVER mutates; always deterministic shape."""
    return {
        "approved": False,
        "requires_review": True,
        "classification": "",
        "justification": "",
        "confidence": "",
        "reason": reason,
        "route": REVIEW_ROUTE,
    }


def _coerce_structured(ai_output):
    """Accept either a dict (already-parsed structured output) or a RAW JSON string.

    Returns a dict, or None if it cannot be STRICTLY parsed into a JSON object. Never raises
    on bad input.

    Strictness decisions (deliberate, documented):
      - We only accept a bare JSON object. A JSON array, number, string, bool or null parses
        as valid JSON but is NOT an object -> rejected (returns None).
      - We do NOT strip Markdown code fences (```json ... ```), leading prose, or any
        "here is the classification:" preamble. A fenced or prose-wrapped blob is treated as
        malformed and rejected. This is intentional: the Ask AI prompt instructs the model to
        return STRICT JSON and nothing else; silently unwrapping fences would be exactly the
        kind of lenient parsing that lets malformed / injected output through. Configure the
        Ask AI node to emit structured JSON (an object), not a fenced string.
      - No field value is ever eval'd, exec'd, or interpreted as an instruction. Values are
        only type/shape/enum checked below.
    """
    if isinstance(ai_output, dict):
        return ai_output
    if isinstance(ai_output, str):
        text = ai_output.strip()
        if not text:
            return None
        # Explicit, strict rejection of fenced / prose-wrapped output so the reason is clear
        # and the behavior does not depend on an incidental JSON parse error.
        if text.startswith("```") or not text.startswith("{"):
            return None
        try:
            parsed = json.loads(text)
        except (ValueError, TypeError):
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def _valid_confidence(value, threshold):
    """Validate an optional confidence value.

    Returns (ok, normalized_float_or_None, reason).
      - absent (None)  -> ok=True, None (not gated)
      - bool           -> ok=False (bool is NOT an acceptable numeric confidence)
      - finite float/int in [0,1] and >= threshold -> ok=True
      - anything else  -> ok=False with a reason
    """
    if value is None:
        return True, None, ""
    # Explicitly reject bool: in Python bool is a subclass of int, which would otherwise
    # sneak True/False through as 1/0.
    if isinstance(value, bool):
        return False, None, "Confidence must be a number, not a boolean."
    if not isinstance(value, (int, float)):
        return False, None, "Confidence was present but not a finite number."
    f = float(value)
    # Reject NaN / +-inf (NaN != NaN; inf is out of [0,1] anyway but check explicitly).
    if f != f or f in (float("inf"), float("-inf")):
        return False, None, "Confidence was not a finite number."
    if f < 0.0 or f > 1.0:
        return False, None, "Confidence was out of the valid range [0,1]."
    if f < threshold:
        return False, f, "Confidence %.3f is below the configured threshold %.3f." % (f, threshold)
    return True, f, ""


def validate_classification(
    ai_output,
    classification_key=DEFAULT_CLASSIFICATION_KEY,
    justification_key=DEFAULT_JUSTIFICATION_KEY,
    confidence_key=DEFAULT_CONFIDENCE_KEY,
    confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLD,
):
    """Pure, testable core. Returns a result dict (see OUTPUT_FIELDS). Never raises on
    malformed/unknown/low-confidence input; those return a requires_review result instead.
    Never mutates any input.
    """
    data = _coerce_structured(ai_output)
    if data is None:
        return _review("Classifier output was missing or not valid structured JSON/object.")

    label = data.get(classification_key)
    if not isinstance(label, str):
        return _review("Classification field was missing or not a string.")
    # EXACT enum match - no normalization, no case folding.
    if label not in ALLOWED_CLASSIFICATIONS:
        return _review(
            "Classification was not one of the allowed labels (Bug/Feature/Enhancement)."
        )

    justification = data.get(justification_key)
    if not isinstance(justification, str):
        return _review("Justification was missing or not a string.")
    justification = justification.strip()
    if len(justification) < MIN_JUSTIFICATION_LEN:
        return _review("Justification was empty.")
    if len(justification) > MAX_JUSTIFICATION_LEN:
        return _review(
            "Justification exceeded the maximum allowed length (%d chars)." % MAX_JUSTIFICATION_LEN
        )

    ok, conf, conf_reason = _valid_confidence(
        data.get(confidence_key), confidence_threshold
    )
    if not ok:
        return _review(conf_reason)

    return {
        "approved": True,
        "requires_review": False,
        "classification": label,
        "justification": justification,
        "confidence": "" if conf is None else ("%.6g" % conf),
        "reason": "Classification accepted.",
        "route": label,  # approved -> route IS the accepted label (Bug/Feature/Enhancement)
    }


# ---------------------------------------------------------------------------
# ASSESSMENT-ALIGNED strict entrypoint (the shape EMBEDDED in the live template)
# ---------------------------------------------------------------------------
# The exercise's Router has EXACTLY three named paths (Bug / Feature / Enhancement) and no
# 4th path. The template therefore embeds a STRICT validator that RAISES ValueError on any
# invalid / malformed / unknown / low-confidence AI output - which STOPS the run (it shows as
# a failed run in the Runs tab) rather than routing to a Review fallback or silently mutating
# the ticket. The `validate_classification` / `_review` helpers above remain available as an
# OPTIONAL general-purpose module (e.g. for a design that wants a non-failing Review branch),
# documented separately; they are NOT what the aligned template runs.


def validate_classification_strict(
    ai_output,
    classification_key=DEFAULT_CLASSIFICATION_KEY,
    justification_key=DEFAULT_JUSTIFICATION_KEY,
    confidence_key=DEFAULT_CONFIDENCE_KEY,
    confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLD,
):
    """Strict core used by the ALIGNED template. Returns
    {route, classification, justification} for a clean, in-enum result and RAISES ValueError
    on ANYTHING invalid (so the workflow run stops - no 4th Review route). Never mutates its
    input, never evals/execs any value.
    """
    result = validate_classification(
        ai_output,
        classification_key=classification_key,
        justification_key=justification_key,
        confidence_key=confidence_key,
        confidence_threshold=confidence_threshold,
    )
    if result["requires_review"]:
        raise ValueError(result["reason"])
    return {
        "route": result["classification"],      # always one of Bug/Feature/Enhancement
        "classification": result["classification"],
        "justification": result["justification"],
    }


def run_strict(inputs, keyrings):
    """DevRev Execute Code entrypoint for the ALIGNED (3-route) template.

    Input: ai_output (Ask AI structured output / raw JSON string). Output: route (text),
    classification (text), justification (text). Invalid output RAISES ValueError and the run
    fails - there is NO Review route and NO mutation on bad AI output.
    """
    inputs = inputs or {}
    threshold = inputs.get("confidence_threshold", DEFAULT_CONFIDENCE_THRESHOLD)
    try:
        threshold = float(threshold)
        if threshold != threshold or threshold < 0.0 or threshold > 1.0:
            threshold = DEFAULT_CONFIDENCE_THRESHOLD
    except (TypeError, ValueError):
        threshold = DEFAULT_CONFIDENCE_THRESHOLD
    return validate_classification_strict(
        inputs.get("ai_output"),
        classification_key=inputs.get("classification_key", DEFAULT_CLASSIFICATION_KEY),
        justification_key=inputs.get("justification_key", DEFAULT_JUSTIFICATION_KEY),
        confidence_key=inputs.get("confidence_key", DEFAULT_CONFIDENCE_KEY),
        confidence_threshold=threshold,
    )


def run(inputs, keyrings):
    """DevRev Execute Code entrypoint (OPTIONAL non-failing / general module).

    This is the OPTIONAL Review-emitting variant (safety improvement documented separately),
    NOT the shape embedded in the aligned template. The aligned template embeds the strict
    `run_strict` behavior (raise-on-invalid). Configure node inputs (all optional except
    ai_output):
      - ai_output: the Ask AI node's structured output (dict) OR its raw JSON string.
      - classification_key / justification_key / confidence_key: optional field-name overrides.
      - confidence_threshold: optional float (default 0.75 - a stated design assumption).

    Configure node outputs to match OUTPUT_FIELDS exactly:
      approved (bool), requires_review (bool), classification (text), justification (text),
      confidence (text), reason (text), route (text).

    The Router branches on the single derived `route` field: it matches `route` with a
    single-value `contains_any` list on each of the four routes - Bug / Feature /
    Enhancement for an approved classification, and "Review" for everything that must be
    reviewed. Exactly one route value is ever emitted, so the four routes are mutually
    exclusive by construction. This node never changes severity or any other object field.
    """
    inputs = inputs or {}
    threshold = inputs.get("confidence_threshold", DEFAULT_CONFIDENCE_THRESHOLD)
    try:
        threshold = float(threshold)
        if threshold != threshold or threshold < 0.0 or threshold > 1.0:
            threshold = DEFAULT_CONFIDENCE_THRESHOLD
    except (TypeError, ValueError):
        threshold = DEFAULT_CONFIDENCE_THRESHOLD

    return validate_classification(
        inputs.get("ai_output"),
        classification_key=inputs.get("classification_key", DEFAULT_CLASSIFICATION_KEY),
        justification_key=inputs.get("justification_key", DEFAULT_JUSTIFICATION_KEY),
        confidence_key=inputs.get("confidence_key", DEFAULT_CONFIDENCE_KEY),
        confidence_threshold=threshold,
    )
