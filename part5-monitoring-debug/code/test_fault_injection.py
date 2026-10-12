"""Part 5 - local fault-injection + recovery tests (NON-live).

These tests check exception handling and recovery with synthetic input. They do not
prove hosted workflow state, an AI explanation, or published-version recovery.

They reuse Part 3's logic without any live API call:

  1. The injected fault makes the validator raise. No workflow engine runs here.
     Both documented fault options are simulated:
       - Option A: a scripted non-success response (e.g. 404) is rejected.
       - Option B: a deterministic injected exception propagates.
     We also show the endpoint allow-list in build_request rejects the Part 5 typo URL before
     any request is even sent.

  2. The FIX recovers: after restoring the correct endpoint / removing the raise, the SAME
     validator accepts a synthetic 2xx works.create response and returns the issue ids.

No comment/notification logic is re-implemented here; Part 5 reuses Part 3 code only.
"""

import os
import sys
import unittest

# Import Part 3's modules directly - Part 5 reuses them, it does not re-implement them.
_PART3_CODE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "part3-http-work-create", "code")
)
if _PART3_CODE not in sys.path:
    sys.path.insert(0, _PART3_CODE)

from validate_response import validate_works_create, WorksCreateError  # noqa: E402
from build_request import validate_endpoint  # noqa: E402


# A synthetic, non-sensitive works.create response (same shape as the Part 3 placeholder).
SYNTHETIC_404_BODY = {"error": {"type": "not_found", "message": "no such endpoint"}}
SYNTHETIC_201_BODY = {
    "work": {
        "id": "don:core:dvrv-REGION-N:devo/SYNTHETIC:issue/777",
        "display_id": "ISS-777",
        "type": "issue",
        "external_ref": "devrevu-p3:TKT-SYNTHETIC",
    }
}


def validator_with_injected_raise(status_code, response_body):
    """Simulates fault Option B: a deterministic raise injected at the top of the node body."""
    raise RuntimeError("Part 5 injected fault")


class TestFaultInjectionFails(unittest.TestCase):
    def test_option_a_wrong_endpoint_rejected_before_request(self):
        # The deliberate typo URL from the fault spec is rejected by the allow-list.
        with self.assertRaises(ValueError):
            validate_endpoint("https://api.devrev.ai/works.create-404")

    def test_option_a_non_2xx_raises_marking_run_failed(self):
        # If a bad endpoint still returns a 404 body, the validator raises -> run fails.
        with self.assertRaises(WorksCreateError) as ctx:
            validate_works_create(404, SYNTHETIC_404_BODY)
        self.assertEqual(ctx.exception.code, "non_2xx")
        # Failure message must not leak the response body.
        self.assertNotIn("not_found", str(ctx.exception))

    def test_option_b_injected_raise_propagates(self):
        with self.assertRaises(RuntimeError):
            validator_with_injected_raise(201, SYNTHETIC_201_BODY)


class TestRecoveryAfterFix(unittest.TestCase):
    def test_fixed_endpoint_accepted(self):
        from build_request import WORKS_CREATE_URL
        self.assertEqual(validate_endpoint(WORKS_CREATE_URL), WORKS_CREATE_URL)

    def test_synthetic_2xx_recovers(self):
        # After the fix, the SAME validator accepts a good synthetic response.
        out = validate_works_create(201, SYNTHETIC_201_BODY)
        self.assertEqual(out["display_id"], "ISS-777")
        self.assertTrue(out["work_id"].endswith("issue/777"))

    def test_no_raise_after_fix(self):
        # Option B fix = remove the injected raise; the normal validator no longer raises.
        try:
            out = validate_works_create(200, SYNTHETIC_201_BODY)
        except Exception as e:  # pragma: no cover - should not happen
            self.fail("validator unexpectedly raised after fix: %r" % e)
        self.assertEqual(out["display_id"], "ISS-777")


if __name__ == "__main__":
    unittest.main()
