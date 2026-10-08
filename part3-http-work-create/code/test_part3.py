import json
import unittest

from build_request import (
    build_works_create_body,
    validate_endpoint,
    WORKS_CREATE_URL,
    run as build_run,
)
from validate_response import (
    validate_works_create,
    verify_conflict_is_same_source,
    WorksCreateError,
    run as validate_run,
)
from reverse_severity import reverse_severity, run as reverse_run
from notify_policy import plan_post_create_actions, NotifyGateError, run as notify_run


class TestBuildRequest(unittest.TestCase):
    def test_builds_valid_body(self):
        body, ext = build_works_create_body(
            ticket_id="TKT-123",
            title="Login fails on Safari",
            applies_to_part_id="don:core:synthetic:part/42",
            owned_by_ids=["don:identity:synthetic:devu/7"],
            severity="low",
        )
        parsed = json.loads(body)
        self.assertEqual(parsed["type"], "issue")
        self.assertEqual(parsed["title"], "Login fails on Safari")
        self.assertEqual(parsed["applies_to_part"], "don:core:synthetic:part/42")
        self.assertEqual(parsed["owned_by"], ["don:identity:synthetic:devu/7"])
        self.assertEqual(parsed["external_ref"], "devrevu-p3:TKT-123")
        self.assertEqual(ext, "devrevu-p3:TKT-123")

    def test_title_required(self):
        with self.assertRaises(ValueError):
            build_works_create_body("T", "  ", "part", ["u"], "low")

    def test_part_required(self):
        with self.assertRaises(ValueError):
            build_works_create_body("T", "Title", "", ["u"], "low")

    def test_owners_required(self):
        with self.assertRaises(ValueError):
            build_works_create_body("T", "Title", "part", [], "low")

    def test_run_shape(self):
        out = build_run({
            "ticket_id": "TKT-9",
            "title": "X marks it",
            "applies_to_part_id": "part",
            "owned_by_ids": ["u1"],
            "severity": "low",
        }, {})
        self.assertEqual(set(out.keys()), {"body", "external_ref", "endpoint"})

    def test_body_is_json_safe_against_injection(self):
        body, _ = build_works_create_body(
            "T", 'Evil" ,"type":"account', "part", ["u"], "low"
        )
        parsed = json.loads(body)  # must still be valid, single issue type
        self.assertEqual(parsed["type"], "issue")
        self.assertIn("Evil", parsed["title"])


class TestValidateResponse(unittest.TestCase):
    def test_2xx_with_work_wrapper(self):
        out = validate_works_create(
            201, {"work": {"id": "don:core:x:issue/5", "display_id": "ISS-5"}}
        )
        self.assertEqual(out, {"work_id": "don:core:x:issue/5", "display_id": "ISS-5"})

    def test_2xx_top_level(self):
        out = validate_works_create(
            200, json.dumps({"id": "don:core:x:issue/6", "display_id": "ISS-6"})
        )
        self.assertEqual(out["display_id"], "ISS-6")

    def test_non_2xx_raises(self):
        with self.assertRaises(WorksCreateError) as ctx:
            validate_works_create(404, {"work": {"id": "a", "display_id": "b"}})
        # must not leak body; message mentions status only
        self.assertIn("404", str(ctx.exception))

    def test_500_raises(self):
        with self.assertRaises(WorksCreateError):
            validate_works_create(500, "")

    def test_2xx_missing_ids_raises(self):
        with self.assertRaises(WorksCreateError):
            validate_works_create(200, {"work": {"id": "only-id"}})

    def test_empty_body_raises(self):
        with self.assertRaises(WorksCreateError):
            validate_works_create(200, "")

    def test_bad_json_raises(self):
        with self.assertRaises(WorksCreateError):
            validate_works_create(200, "{not json")

    def test_bad_status_raises(self):
        with self.assertRaises(WorksCreateError):
            validate_works_create(None, {"work": {"id": "a", "display_id": "b"}})

    def test_error_message_does_not_leak_body(self):
        secret = "Bearer super-secret-token-should-not-appear"
        with self.assertRaises(WorksCreateError) as ctx:
            validate_works_create(403, {"error": secret})
        self.assertNotIn("secret", str(ctx.exception).lower())

    def test_run_entrypoint(self):
        out = validate_run({
            "status_code": 201,
            "response_body": {"work": {"id": "i", "display_id": "ISS-1"}},
        }, {})
        self.assertEqual(out["display_id"], "ISS-1")


class TestReverseSeverity(unittest.TestCase):
    def test_low(self):
        self.assertEqual(reverse_severity("low")["reversed"], "wol")

    def test_high(self):
        self.assertEqual(reverse_severity("high")["reversed"], "hgih")

    def test_blocker(self):
        self.assertEqual(reverse_severity("blocker")["reversed"], "rekcolb")

    def test_case_and_space(self):
        self.assertEqual(reverse_severity("  LOW ")["reversed"], "wol")

    def test_invalid_raises(self):
        with self.assertRaises(ValueError):
            reverse_severity("urgent")

    def test_non_string_raises(self):
        with self.assertRaises(ValueError):
            reverse_severity(None)

    def test_run_entrypoint(self):
        self.assertEqual(reverse_run({"severity": "medium"}, {})["reversed"], "muidem")


class TestEndpointValidation(unittest.TestCase):
    def test_fixed_https_endpoint_accepted(self):
        self.assertEqual(validate_endpoint(WORKS_CREATE_URL), WORKS_CREATE_URL)

    def test_trims_whitespace(self):
        self.assertEqual(validate_endpoint("  " + WORKS_CREATE_URL + " "), WORKS_CREATE_URL)

    def test_http_downgrade_rejected(self):
        with self.assertRaises(ValueError):
            validate_endpoint("http://api.devrev.ai/works.create")

    def test_wrong_host_rejected(self):
        with self.assertRaises(ValueError):
            validate_endpoint("https://evil.example.com/works.create")

    def test_credentials_in_host_rejected(self):
        with self.assertRaises(ValueError):
            validate_endpoint("https://user:pass@evil.example.com/works.create")

    def test_wrong_path_rejected(self):
        # The Part 5 fault-injection typo must be rejected here.
        with self.assertRaises(ValueError):
            validate_endpoint("https://api.devrev.ai/works.create-404")

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            validate_endpoint("")

    def test_build_run_returns_validated_endpoint(self):
        out = build_run({
            "ticket_id": "TKT-1", "title": "T", "applies_to_part_id": "part",
            "owned_by_ids": ["u1"], "severity": "low",
        }, {})
        self.assertEqual(out["endpoint"], WORKS_CREATE_URL)

    def test_build_run_rejects_bad_endpoint(self):
        with self.assertRaises(ValueError):
            build_run({
                "ticket_id": "TKT-1", "title": "T", "applies_to_part_id": "part",
                "owned_by_ids": ["u1"], "severity": "low",
                "endpoint": "http://api.devrev.ai/works.create",
            }, {})


class TestOwnerAndUnsafeInput(unittest.TestCase):
    def test_owner_must_be_nonempty_strings(self):
        with self.assertRaises(ValueError):
            build_works_create_body("T", "Title", "part", ["", "u2"], "low")

    def test_owner_non_string_rejected(self):
        with self.assertRaises(ValueError):
            build_works_create_body("T", "Title", "part", [123], "low")

    def test_owner_not_a_list_rejected(self):
        with self.assertRaises(ValueError):
            build_works_create_body("T", "Title", "part", "u1", "low")

    def test_unicode_and_quotes_encoded_safely(self):
        tricky = 'Café "quote"   line sep \\ backslash'
        body, _ = build_works_create_body("T", tricky, "part", ["u1"], "low")
        parsed = json.loads(body)  # must round-trip without breaking JSON
        self.assertEqual(parsed["title"], tricky)

    def test_title_too_long_rejected(self):
        with self.assertRaises(ValueError):
            build_works_create_body("T", "x" * 257, "part", ["u1"], "low")


class TestStatusCodeBranching(unittest.TestCase):
    def test_429_rate_limited_code(self):
        with self.assertRaises(WorksCreateError) as ctx:
            validate_works_create(429, {"work": {"id": "a", "display_id": "b"}})
        self.assertEqual(ctx.exception.code, "rate_limited")

    def test_409_conflict_code(self):
        with self.assertRaises(WorksCreateError) as ctx:
            validate_works_create(409, {"work": {"id": "a", "display_id": "b"}})
        self.assertEqual(ctx.exception.code, "conflict")

    def test_404_non_2xx_code(self):
        with self.assertRaises(WorksCreateError) as ctx:
            validate_works_create(404, "")
        self.assertEqual(ctx.exception.code, "non_2xx")

    def test_bad_status_code(self):
        with self.assertRaises(WorksCreateError) as ctx:
            validate_works_create(None, "")
        self.assertEqual(ctx.exception.code, "bad_status")

    def test_2xx_missing_ids_code(self):
        with self.assertRaises(WorksCreateError) as ctx:
            validate_works_create(201, {"work": {"id": "only"}})
        self.assertEqual(ctx.exception.code, "bad_response")


class TestConflictReuse(unittest.TestCase):
    def test_reuse_only_when_same_external_ref(self):
        body = {"work": {"id": "i1", "display_id": "ISS-1", "external_ref": "devrevu-p3:TKT-9"}}
        out = verify_conflict_is_same_source(body, "devrevu-p3:TKT-9")
        self.assertEqual(out, {"work_id": "i1", "display_id": "ISS-1"})

    def test_no_reuse_when_different_source(self):
        body = {"work": {"id": "i1", "display_id": "ISS-1", "external_ref": "devrevu-p3:OTHER"}}
        self.assertIsNone(verify_conflict_is_same_source(body, "devrevu-p3:TKT-9"))

    def test_no_reuse_when_no_external_ref(self):
        body = {"work": {"id": "i1", "display_id": "ISS-1"}}
        self.assertIsNone(verify_conflict_is_same_source(body, "devrevu-p3:TKT-9"))

    def test_no_reuse_when_expected_ref_blank(self):
        body = {"work": {"id": "i1", "display_id": "ISS-1", "external_ref": "x"}}
        self.assertIsNone(verify_conflict_is_same_source(body, ""))


class TestNotifyGate(unittest.TestCase):
    def test_plan_after_verified_create(self):
        out = plan_post_create_actions(
            {"work_id": "don:...:issue/5", "display_id": "ISS-5"}, "wol", "don:identity:x:devu/7"
        )
        self.assertTrue(out["should_notify"])
        self.assertEqual(out["notification"], "ISS-5 has been created for your ticket.")
        self.assertIn("wol", out["issue_comment"])

    def test_no_notify_without_verified_create(self):
        with self.assertRaises(NotifyGateError):
            plan_post_create_actions(None, "wol", "owner")

    def test_no_notify_when_ids_missing(self):
        with self.assertRaises(NotifyGateError):
            plan_post_create_actions({"work_id": "i", "display_id": ""}, "wol", "owner")

    def test_missing_reversed_severity(self):
        with self.assertRaises(NotifyGateError):
            plan_post_create_actions({"work_id": "i", "display_id": "ISS-1"}, "", "owner")

    def test_missing_owner(self):
        with self.assertRaises(NotifyGateError):
            plan_post_create_actions({"work_id": "i", "display_id": "ISS-1"}, "wol", "")

    def test_run_entrypoint(self):
        out = notify_run({
            "create_result": {"work_id": "i", "display_id": "ISS-9"},
            "reversed_severity": "hgih",
            "ticket_owner_id": "owner",
        }, {})
        self.assertEqual(out["notification"], "ISS-9 has been created for your ticket.")


if __name__ == "__main__":
    unittest.main()
