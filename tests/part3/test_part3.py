import json
import os
import sys
import unittest

# Part 3's Execute Code modules live in the part folder; tests are centralized here.
_PART3_CODE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "part3-http-work-create", "code")
)
if _PART3_CODE not in sys.path:
    sys.path.insert(0, _PART3_CODE)

from build_request import (  # noqa: E402
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

# The generated importable template + its generator live in the part folder's tools/.
_PART3_TOOLS = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "part3-http-work-create", "tools")
)
if _PART3_TOOLS not in sys.path:
    sys.path.insert(0, _PART3_TOOLS)
import gen_template  # noqa: E402

_PART3_TEMPLATE = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "..", "part3-http-work-create", "templates",
        "12-Part 3-template.json",
    )
)


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


def _exec_code_module(code_text):
    """Execute an embedded invoke_code body in an isolated namespace and return it."""
    ns = {}
    exec(code_text, ns)  # noqa: S102 - trusted, generated-in-repo code under test
    return ns


class TestGeneratedTemplate(unittest.TestCase):
    """Structure/regression tests for the generated Part 3 import template.

    All shapes are grounded in the PUBLIC shashankcube/computer-skill v2 examples; these
    tests assert the generator keeps producing a valid v2 envelope and that the committed
    file matches the generator output (so it cannot silently drift).
    """

    def setUp(self):
        self.envelope = gen_template.build_envelope()
        self.inner = json.loads(self.envelope["data"])
        self.steps = {s["reference_key"]: s for s in self.inner["steps"]}

    def test_envelope_shape(self):
        self.assertEqual(set(self.envelope.keys()), {"data", "templateVersion"})
        self.assertEqual(self.envelope["templateVersion"], "2.0.0")
        self.assertIsInstance(self.envelope["data"], str)

    def test_inner_serialization_v2(self):
        self.assertEqual(self.inner["serialization_version"]["major"], 2)
        self.assertIn("title", self.inner)
        self.assertIn("steps", self.inner)

    def test_committed_file_matches_generator(self):
        with open(_PART3_TEMPLATE, encoding="utf-8") as fh:
            on_disk = json.load(fh)
        # Inner JSON must be semantically identical (ordering-independent).
        self.assertEqual(json.loads(on_disk["data"]), self.inner)
        self.assertEqual(on_disk["templateVersion"], "2.0.0")

    def test_all_referenced_steps_exist(self):
        refs = set(self.steps.keys())
        for s in self.inner["steps"]:
            for n in s.get("next_steps", []):
                self.assertIn(n["next_step_reference_key"], refs,
                              "dangling next_step from %s" % s["reference_key"])

    def test_expected_operations_present(self):
        slugs = [s["operation"]["slug"] for s in self.inner["steps"]]
        for required in ("ticket_created", "invoke_code", "http", "add_comment",
                         "if_else", "send_notification"):
            self.assertIn(required, slugs)
        # Mandatory HTTP exercise: there is a real HTTP works.create node (not a native create).
        http_nodes = [s for s in self.inner["steps"] if s["operation"]["slug"] == "http"]
        self.assertEqual(len(http_nodes), 1)

    def test_http_node_is_bearer_post_to_works_create(self):
        http = self.steps["http_works_create_1"]
        fields = {f["name"]: f["value"] for f in http["input_values"][0]["fields"]}
        self.assertEqual(fields["method"], {"type": "literal", "value": "POST"})
        self.assertEqual(fields["auth_type"], {"type": "literal", "value": "Bearer"})
        self.assertEqual(fields["enable_retries"], {"type": "literal", "value": False})
        self.assertEqual(fields["url"]["value"], gen_template.WORKS_CREATE_URL)
        self.assertEqual(fields["url"]["type"], "text_template")
        # Content-Type: application/json header present.
        header_items = fields["headers"]["value"]["items"][0]["value"][0]["fields"]
        hp = {f["name"]: f["value"]["value"] for f in header_items}
        self.assertEqual(hp["key"], "Content-Type")
        self.assertEqual(hp["value"], "application/json")

    def test_http_output_exposes_status_and_body(self):
        http = self.steps["http_works_create_1"]
        out = [p for p in http["output_ports"] if p["name"] == "output"][0]
        names = {d["data_name"] for d in out["schema"]["field_descriptors"]}
        self.assertIn("status_code", names)
        self.assertIn("body", names)

    def test_invoke_code_nodes_complete(self):
        for ref in ("build_request_1", "validate_response_1", "reverse_severity_1", "notify_policy_1"):
            s = self.steps[ref]
            fields = {f["name"] for f in s["input_values"][0]["fields"]}
            self.assertEqual(fields, {"code", "input_values", "output_schema"}, ref)
            # code is text_template, input_values is list_value>composite_value_list, output_schema literal
            fmap = {f["name"]: f["value"] for f in s["input_values"][0]["fields"]}
            self.assertEqual(fmap["code"]["type"], "text_template")
            self.assertEqual(fmap["input_values"]["type"], "list_value")
            self.assertEqual(
                fmap["input_values"]["value"]["items"][0]["type"], "composite_value_list")
            self.assertEqual(fmap["output_schema"]["type"], "literal")
            self.assertTrue(fmap["output_schema"]["value"]["fields"])
            # output port resolves field_descriptors matching the output_schema names
            out = [p for p in s["output_ports"] if p["name"] == "output"][0]
            out_names = {d["data_name"] for d in out["schema"]["field_descriptors"]}
            schema_names = {f["name"] for f in fmap["output_schema"]["value"]["fields"]}
            self.assertEqual(out_names, schema_names, ref)

    def test_owner_mapping_uses_jsonata_map(self):
        # Sourcing the owner list must use JSONata $map (official expression language), not bare map.
        br = self.steps["build_request_1"]
        items = [f for f in br["input_values"][0]["fields"] if f["name"] == "input_values"][0]
        vars_ = items["value"]["value"]["items"][0]["value"]
        owned = None
        for v in vars_:
            fmap = {f["name"]: f["value"] for f in v["fields"]}
            if fmap["name"]["value"] == "owned_by_ids":
                owned = fmap["value"]
        self.assertIsNotNone(owned)
        self.assertEqual(owned["type"], "jsonata_expression")
        self.assertIn("$map(", owned["value"])

    def test_notify_gate_is_native_if_else_true_to_send(self):
        gate = self.steps["notify_gate_1"]
        self.assertEqual(gate["operation"]["slug"], "if_else")
        port_names = {p["name"] for p in gate["output_ports"]}
        self.assertIn("true", port_names)
        self.assertIn("false", port_names)
        # true branch -> send_notification; false branch has NO next step (safe end).
        nexts = {n["port_name"]: n["next_step_reference_key"] for n in gate.get("next_steps", [])}
        self.assertEqual(nexts.get("true"), "send_notification_1")
        self.assertNotIn("false", nexts)

    def test_send_notification_receiver_is_dynamic_from_trigger(self):
        sn = self.steps["send_notification_1"]
        fields = {f["name"]: f["value"] for f in sn["input_values"][0]["fields"]}
        recv = fields["receivers"]
        self.assertEqual(recv["type"], "list_value")
        item = recv["value"]["items"][0]
        self.assertEqual(item["type"], "jsonata_expression")
        self.assertIn("owned_by", item["value"])
        self.assertIn("ticket_created_1", item["value"])

    def test_no_raw_credentials_in_template(self):
        raw = self.envelope["data"]
        import re as _re
        self.assertIsNone(_re.search(r"Bearer\s+[A-Za-z0-9._-]{8,}", raw))
        self.assertNotIn("REPLACE_WITH_YOUR_USER_DON_ID", raw)


class TestEmbeddedCodeGuards(unittest.TestCase):
    """Execute the embedded invoke_code bodies with synthetic fixtures (no HTTP, no network)."""

    def setUp(self):
        inner = json.loads(gen_template.build_envelope()["data"])
        self.code = {}
        for s in inner["steps"]:
            if s["operation"]["slug"] == "invoke_code":
                for f in s["input_values"][0]["fields"]:
                    if f["name"] == "code":
                        self.code[s["reference_key"]] = f["value"]["value"]

    def test_build_request_blocked_by_default(self):
        mod = _exec_code_module(self.code["build_request_1"])
        self.assertFalse(mod["ALLOW_LIVE_CREATE"])
        self.assertEqual(mod["EXPECTED_PART_ID"], "")
        self.assertEqual(mod["EXPECTED_TEST_OWNER_ID"], "")
        with self.assertRaises(ValueError):
            mod["run"]({"ticket_id": "T", "title": "T", "applies_to_part_id": "p",
                        "owned_by_ids": ["u"], "severity": "low"})

    def test_build_request_scope_mismatch_fails(self):
        mod = _exec_code_module(self.code["build_request_1"])
        mod["ALLOW_LIVE_CREATE"] = True
        mod["EXPECTED_PART_ID"] = "don:core:x:part/9"
        mod["EXPECTED_TEST_OWNER_ID"] = "don:id:x:devu/7"
        with self.assertRaises(ValueError):  # wrong part
            mod["run"]({"ticket_id": "T", "title": "T", "applies_to_part_id": "don:core:x:part/BAD",
                        "owned_by_ids": ["don:id:x:devu/7"], "severity": "low"})
        with self.assertRaises(ValueError):  # non-low severity
            mod["run"]({"ticket_id": "T", "title": "T", "applies_to_part_id": "don:core:x:part/9",
                        "owned_by_ids": ["don:id:x:devu/7"], "severity": "high"})

    def test_build_request_opted_in_builds_body(self):
        mod = _exec_code_module(self.code["build_request_1"])
        mod["ALLOW_LIVE_CREATE"] = True
        mod["EXPECTED_PART_ID"] = "don:core:x:part/9"
        mod["EXPECTED_TEST_OWNER_ID"] = "don:id:x:devu/7"
        out = mod["run"]({"ticket_id": "TKT-1", "title": "Login bug",
                          "applies_to_part_id": "don:core:x:part/9",
                          "owned_by_ids": ["don:id:x:devu/7"], "severity": "low"})
        parsed = json.loads(out["body"])
        self.assertEqual(parsed["type"], "issue")
        self.assertEqual(out["external_ref"], "devrevu-p3:TKT-1")

    def test_validate_response_non_2xx_raises_no_http(self):
        mod = _exec_code_module(self.code["validate_response_1"])
        with self.assertRaises(Exception):
            mod["run"]({"status_code": 404, "response_body": ""})
        ok = mod["run"]({"status_code": 201,
                         "response_body": {"work": {"id": "don:x:issue/5", "display_id": "ISS-5"}}})
        self.assertEqual(ok["display_id"], "ISS-5")

    def test_reverse_severity_embedded(self):
        mod = _exec_code_module(self.code["reverse_severity_1"])
        self.assertEqual(mod["run"]({"severity": "low"})["reversed"], "wol")

    def test_notify_policy_default_off(self):
        mod = _exec_code_module(self.code["notify_policy_1"])
        self.assertFalse(mod["ALLOW_OWNER_NOTIFICATION"])
        out = mod["run"]({"work_id": "i", "display_id": "ISS-5", "reversed_severity": "wol",
                          "ticket_owner_id": "don:id:x:devu/7"})
        self.assertFalse(out["should_notify"])
        self.assertEqual(out["notification"], "ISS-5 has been created for your ticket.")

    def test_notify_policy_enabled_matched_owner(self):
        mod = _exec_code_module(self.code["notify_policy_1"])
        mod["ALLOW_OWNER_NOTIFICATION"] = True
        mod["EXPECTED_TEST_OWNER_ID"] = "don:id:x:devu/7"
        on = mod["run"]({"work_id": "i", "display_id": "ISS-5", "reversed_severity": "wol",
                         "ticket_owner_id": "don:id:x:devu/7"})
        self.assertTrue(on["should_notify"])
        off = mod["run"]({"work_id": "i", "display_id": "ISS-5", "reversed_severity": "wol",
                          "ticket_owner_id": "don:id:x:devu/OTHER"})
        self.assertFalse(off["should_notify"])

    def test_notify_policy_owner_binding_output_schema_strings(self):
        # Dynamic owner binding + output ids are legitimate non-empty strings.
        mod = _exec_code_module(self.code["notify_policy_1"])
        out = mod["run"]({"work_id": "don:x:issue/5", "display_id": "ISS-5",
                          "reversed_severity": "wol", "ticket_owner_id": "don:id:x:devu/7"})
        for k in ("work_id", "display_id", "notification", "issue_comment"):
            self.assertIsInstance(out[k], str)
            self.assertTrue(out[k])


if __name__ == "__main__":
    unittest.main()
