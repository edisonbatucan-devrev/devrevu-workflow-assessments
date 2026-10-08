"""Python SEMANTIC-PARITY TWIN of src/core/business_hours.core.mjs / .ts.

WHY THIS FILE EXISTS: the snap-in's real logic is the TypeScript/.mjs core. The authoring
environment here has NO Node.js, so the .mjs tests cannot be executed. To still have the
business logic actually RUN and be verified locally, this module reimplements the SAME
algorithm in dependency-free Python, and test_business_hours_core.py runs the SAME scenarios.

This is a hand-synced twin, NOT the deployed artifact. If you change the .mjs/.ts core, change
this too. Semantic parity is asserted by mirroring the same scenarios in both test suites.

Algorithm (identical to the JS core):
  - Validate the timestamp (ISO-8601 with offset / Z); reject empty/garbage.
  - evaluate(id, instant) is injected and returns {"instant_evaluations": [eval]}.
  - Each used evaluation must be "defined"; undefined/unknown definedness RAISES
    (schedule_undefined) rather than guessing "offline".
  - If active -> within hours, next_open_time empty (ignore any next_transition, which is a
    CLOSING time when active).
  - If inactive -> follow next_transition candidates (strictly advancing, bounded) and verify
    an active instant; if none verified within the bound, return empty next_open_time (never
    fabricate one).
"""

from datetime import datetime, timezone

MAX_TRANSITION_HOPS = 8
DEFINED_DEFINEDNESS = frozenset({"defined", "DEFINED"})


class ScheduleError(Exception):
    def __init__(self, message, code="schedule_error"):
        super().__init__(message)
        self.code = code


def parse_timestamp(ts):
    """Return epoch milliseconds. Raises ScheduleError('bad_timestamp') on bad input.

    Accepts ISO-8601 with 'Z' or a numeric offset. Mirrors Date.parse's accepted subset for
    the shapes used by the exercise (offset timestamps).
    """
    if not isinstance(ts, str) or ts.strip() == "":
        raise ScheduleError("timestamp is required (non-empty string)", "bad_timestamp")
    text = ts.strip()
    # datetime.fromisoformat (3.9) does not accept trailing 'Z'; normalize it.
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        raise ScheduleError("timestamp is not a valid ISO-8601 datetime", "bad_timestamp")
    if dt.tzinfo is None:
        # Require an explicit offset, matching the "offset timestamp" requirement.
        raise ScheduleError("timestamp must include a UTC offset", "bad_timestamp")
    return int(dt.timestamp() * 1000)


def _to_iso(ms):
    return (
        datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _pick_evaluation(resp):
    evals = (resp or {}).get("instant_evaluations")
    if not isinstance(evals, list) or len(evals) == 0:
        raise ScheduleError(
            "org-schedules.evaluate returned no instant_evaluations", "schedule_unavailable"
        )
    return evals[0]


def _assert_defined(ev):
    d = (ev or {}).get("definedness")
    if d is None:
        if isinstance((ev or {}).get("is_active"), bool):
            return  # tolerate omission when is_active is an explicit bool
        raise ScheduleError("schedule evaluation definedness is missing", "schedule_undefined")
    if d not in DEFINED_DEFINEDNESS:
        raise ScheduleError(
            "schedule does not define this instant (definedness != defined)",
            "schedule_undefined",
        )


def evaluate_business_hours(org_schedule_id, timestamp, evaluate):
    """evaluate(id, instant_iso) -> {"instant_evaluations": [eval]}. Returns a result dict."""
    if not isinstance(org_schedule_id, str) or org_schedule_id.strip() == "":
        raise ScheduleError("org_schedule_id is required", "bad_input")
    if not callable(evaluate):
        raise ScheduleError("evaluate function must be injected", "bad_input")

    at_ms = parse_timestamp(timestamp)
    at_iso = _to_iso(at_ms)

    first = _pick_evaluation(evaluate(org_schedule_id, at_iso))
    _assert_defined(first)
    if first.get("is_active") is True:
        return {"is_within_business_hours": True, "next_open_time": "", "evaluated_at": at_iso}

    candidate = first.get("next_transition")
    for _ in range(MAX_TRANSITION_HOPS):
        if not isinstance(candidate, str) or candidate.strip() == "":
            return {"is_within_business_hours": False, "next_open_time": "", "evaluated_at": at_iso}
        try:
            cand_ms = parse_timestamp(candidate)
        except ScheduleError:
            return {"is_within_business_hours": False, "next_open_time": "", "evaluated_at": at_iso}
        if cand_ms <= at_ms:  # non-advancing / past
            return {"is_within_business_hours": False, "next_open_time": "", "evaluated_at": at_iso}
        ev = _pick_evaluation(evaluate(org_schedule_id, _to_iso(cand_ms)))
        _assert_defined(ev)
        if ev.get("is_active") is True:
            return {
                "is_within_business_hours": False,
                "next_open_time": _to_iso(cand_ms),
                "evaluated_at": at_iso,
            }
        candidate = ev.get("next_transition")
    return {"is_within_business_hours": False, "next_open_time": "", "evaluated_at": at_iso}
