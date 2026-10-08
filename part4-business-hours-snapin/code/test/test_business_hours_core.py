"""Runnable tests for the Python semantic-parity twin of the Business Hours core.

These mirror the scenarios in business_hours.core.test.mjs so the logic is actually executed
locally even without Node. Run: python3 -m unittest -v (from this directory).
"""

import unittest

from business_hours_core import (
    evaluate_business_hours,
    parse_timestamp,
    ScheduleError,
    MAX_TRANSITION_HOPS,
)


def fake_evaluate(script):
    def _ev(_id, instant_iso):
        if instant_iso not in script:
            raise AssertionError("unexpected instant queried: " + instant_iso)
        return {"instant_evaluations": [script[instant_iso]]}
    return _ev


class TestBusinessHoursCore(unittest.TestCase):
    def test_within_hours_true_no_next(self):
        ts = "2026-10-08T10:00:00.000Z"
        r = evaluate_business_hours("s", ts, fake_evaluate(
            {ts: {"definedness": "defined", "is_active": True, "next_transition": None}}))
        self.assertTrue(r["is_within_business_hours"])
        self.assertEqual(r["next_open_time"], "")
        self.assertEqual(r["evaluated_at"], ts)

    def test_outside_with_verified_next_opening(self):
        ts = "2026-10-08T22:00:00.000Z"
        nxt = "2026-10-09T01:00:00.000Z"
        r = evaluate_business_hours("s", ts, fake_evaluate({
            ts: {"definedness": "defined", "is_active": False, "next_transition": nxt},
            nxt: {"definedness": "defined", "is_active": True, "next_transition": None},
        }))
        self.assertFalse(r["is_within_business_hours"])
        self.assertEqual(r["next_open_time"], nxt)

    def test_weekend_no_transition_empty_next(self):
        ts = "2026-10-10T10:00:00.000Z"
        r = evaluate_business_hours("s", ts, fake_evaluate(
            {ts: {"definedness": "defined", "is_active": False, "next_transition": None}}))
        self.assertFalse(r["is_within_business_hours"])
        self.assertEqual(r["next_open_time"], "")

    def test_holiday_bounded_follow(self):
        ts = "2026-12-25T10:00:00.000Z"
        t1 = "2026-12-26T01:00:00.000Z"
        t2 = "2026-12-28T01:00:00.000Z"
        r = evaluate_business_hours("s", ts, fake_evaluate({
            ts: {"is_active": False, "next_transition": t1},
            t1: {"is_active": False, "next_transition": t2},
            t2: {"is_active": True, "next_transition": None},
        }))
        self.assertEqual(r["next_open_time"], t2)

    def test_non_advancing_transition_empty(self):
        ts = "2026-10-08T22:00:00.000Z"
        past = "2026-10-08T09:00:00.000Z"
        r = evaluate_business_hours("s", ts, fake_evaluate(
            {ts: {"is_active": False, "next_transition": past}}))
        self.assertEqual(r["next_open_time"], "")

    def test_invalid_timestamp_raises(self):
        with self.assertRaises(ScheduleError) as c:
            evaluate_business_hours("s", "not-a-date", lambda *_: {})
        self.assertEqual(c.exception.code, "bad_timestamp")

    def test_empty_timestamp_raises(self):
        with self.assertRaises(ScheduleError):
            evaluate_business_hours("s", "", lambda *_: {})

    def test_naive_timestamp_rejected(self):
        with self.assertRaises(ScheduleError) as c:
            evaluate_business_hours("s", "2026-10-08T10:00:00", lambda *_: {})
        self.assertEqual(c.exception.code, "bad_timestamp")

    def test_missing_org_id_raises(self):
        with self.assertRaises(ScheduleError) as c:
            evaluate_business_hours("", "2026-10-08T10:00:00Z", lambda *_: {})
        self.assertEqual(c.exception.code, "bad_input")

    def test_schedule_unavailable_not_offline(self):
        ts = "2026-10-08T10:00:00.000Z"
        with self.assertRaises(ScheduleError) as c:
            evaluate_business_hours("s", ts, lambda *_: {"instant_evaluations": []})
        self.assertEqual(c.exception.code, "schedule_unavailable")

    def test_undefined_definedness_raises(self):
        ts = "2027-01-01T10:00:00.000Z"
        with self.assertRaises(ScheduleError) as c:
            evaluate_business_hours("s", ts, fake_evaluate(
                {ts: {"definedness": "undefined", "is_active": False, "next_transition": None}}))
        self.assertEqual(c.exception.code, "schedule_undefined")

    def test_unknown_definedness_raises(self):
        ts = "2027-01-01T10:00:00.000Z"
        with self.assertRaises(ScheduleError) as c:
            evaluate_business_hours("s", ts, fake_evaluate(
                {ts: {"definedness": "unknown", "is_active": True, "next_transition": None}}))
        self.assertEqual(c.exception.code, "schedule_undefined")

    def test_bounded_loop(self):
        ts = "2026-10-08T00:00:00.000Z"
        calls = {"n": 0}

        def ev(_id, instant_iso):
            calls["n"] += 1
            nxt_ms = parse_timestamp(instant_iso) + 3_600_000
            from business_hours_core import _to_iso
            return {"instant_evaluations": [
                {"is_active": False, "next_transition": _to_iso(nxt_ms)}]}

        r = evaluate_business_hours("s", ts, ev)
        self.assertFalse(r["is_within_business_hours"])
        self.assertEqual(r["next_open_time"], "")
        self.assertLessEqual(calls["n"], 1 + MAX_TRANSITION_HOPS)

    def test_timeout_abort_propagates(self):
        ts = "2026-10-08T10:00:00.000Z"

        def timing_out(_id, _iso):
            raise TimeoutError("The operation was aborted")

        with self.assertRaises(TimeoutError):
            evaluate_business_hours("s", ts, timing_out)

    def test_dst_spring_forward_next_opening(self):
        ts = "2026-03-08T06:30:00.000Z"
        open_ = "2026-03-09T13:00:00.000Z"
        r = evaluate_business_hours("s", ts, fake_evaluate({
            ts: {"definedness": "defined", "is_active": False, "next_transition": open_},
            open_: {"definedness": "defined", "is_active": True, "next_transition": None},
        }))
        self.assertEqual(r["next_open_time"], open_)

    def test_active_with_closing_transition_no_next_open(self):
        ts = "2026-10-08T10:00:00.000Z"
        r = evaluate_business_hours("s", ts, fake_evaluate(
            {ts: {"definedness": "defined", "is_active": True,
                  "next_transition": "2026-10-08T18:00:00.000Z"}}))
        self.assertTrue(r["is_within_business_hours"])
        self.assertEqual(r["next_open_time"], "")

    def test_parse_timestamp_epoch(self):
        self.assertEqual(parse_timestamp("1970-01-01T00:00:00.000Z"), 0)


if __name__ == "__main__":
    unittest.main()
