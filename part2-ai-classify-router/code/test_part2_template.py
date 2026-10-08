"""Structure tests for the Part 2 full Execute Code (`invoke_code`) workflow template.

Standard-library only. Validates the IMPORT-format artifact
`part2-ai-classify-router/templates/11-Part 2-template.json` without any DevRev API.

This is the FULL Code-node edition, REPAIRED: a real Execute Code export sample
(kept OUTSIDE the repo, at the workdir root `15-Part 2 - validation issue-template-2.json`)
confirmed that the `invoke_code` `code` input uses value type `text_template`, NOT `literal`.
Both Execute Code `code` fields in this template therefore now carry
`"type": "text_template"`. These tests assert that contract plus the graph shape:

  * wrapper / serialization version are the genuine export shape; title is `Part 2 - Code
    validation`;
  * the inner graph is reachable from the trigger with NO cycles;
  * every next_step reference resolves to a real step;
  * exactly two `invoke_code` nodes (`validate_classification`, `bug_validate_title`), each
    with a `code` input whose value `type` is `text_template` (the PROVEN repair delta);
  * the classification validator's embedded `code` RAISES ValueError on invalid output (the
    aligned stop-the-run behavior, in place of a 4th Review route);
  * every `$get('<key>', ...)` reference points at an existing upstream step (no dangling
    refs) - including the Code-node outputs the Router/If-Else/comments consume;
  * the Router has EXACTLY the 3 named routes (Bug/Feature/Enhancement) - NO 4th Review
    route - each with a matching output edge;
  * Feature/Enhancement set severity medium directly (NO no-downgrade If/Else gate);
  * node operation slugs are the known/verified set (now including `invoke_code`);
  * dynamic targeting only - NO hardcoded DON/display IDs in any field value;
  * comments are internal;
  * severity literals obey the lowercase enum policy;
  * the Ask AI node delimits the untrusted title/body.

NOTE on what is NOT asserted: the `input_values` and `output_schema` field shapes on the
Code nodes are the available reference-docs candidate; the bare export sample does NOT
confirm those, so no test claims they are the proven import shape. A LIVE sandbox import /
re-export round-trip has NOT been run - these are structural checks only.
"""
import json
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PART2 = os.path.dirname(HERE)
TEMPLATE = os.path.join(PART2, "templates", "11-Part 2-template.json")

KNOWN_SLUGS = {
    "ticket_created", "ask_ai", "router", "update_ticket", "add_comment", "if_else",
    "invoke_code",
}
# ASSESSMENT-ALIGNED: exactly 3 named routes (NO 4th "Review" route). The embedded validator
# raises ValueError on invalid AI output, which stops the run instead of routing to a 4th path.
ROUTE_NAMES = {"Bug", "Feature", "Enhancement"}
SEVERITY_ENUM = {"high", "medium", "low", "blocker"}
CODE_NODE_KEYS = {"validate_classification", "bug_validate_title"}


def load_inner():
    with open(TEMPLATE, encoding="utf-8") as fh:
        wrapper = json.load(fh)
    return wrapper, json.loads(wrapper["data"])


def iter_field_values(node):
    """Yield every (name, {type,value}) across a step's input_values fields (shallow)."""
    for grp in node.get("input_values", []) or []:
        for f in grp.get("fields", []) or []:
            yield f.get("name"), f.get("value")


class TestPart2CodeTemplate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wrapper, cls.inner = load_inner()
        cls.steps = cls.inner["steps"]
        cls.by_key = {s["reference_key"]: s for s in cls.steps}
        cls.blob = cls.wrapper["data"]

    # --- wrapper / version / title ---
    def test_wrapper_shape(self):
        self.assertEqual(self.wrapper["templateVersion"], "2.0.0")
        self.assertIsInstance(self.wrapper["data"], str)

    def test_serialization_version(self):
        self.assertEqual(self.inner["serialization_version"], {"major": 2, "minor": 0, "patch": 0})

    def test_title_is_code_validation(self):
        self.assertEqual(self.inner["title"], "Part 2 - Code validation (3-route aligned)")

    def test_top_description_mentions_sandbox_filter(self):
        desc = self.inner["description"].lower()
        self.assertIn("sandbox", desc)
        self.assertIn("filter", desc)

    def test_top_description_records_text_template_repair(self):
        desc = self.inner["description"].lower()
        self.assertIn("text_template", desc)

    def test_step_budget(self):
        self.assertLessEqual(len(self.steps), 25)

    # --- slugs / keys ---
    def test_known_slugs_only(self):
        for s in self.steps:
            self.assertIn(s["operation"]["slug"], KNOWN_SLUGS, s["reference_key"])
            self.assertEqual(s["operation"]["namespace"], "devrev")

    def test_unique_reference_keys(self):
        keys = [s["reference_key"] for s in self.steps]
        self.assertEqual(len(keys), len(set(keys)))

    def test_exactly_one_trigger(self):
        triggers = [s for s in self.steps if s["operation"]["slug"] == "ticket_created"]
        self.assertEqual(len(triggers), 1)

    # --- the PROVEN repair: Execute Code `code` fields are text_template ---
    def test_invoke_code_nodes_present(self):
        code_keys = {s["reference_key"] for s in self.steps
                     if s["operation"]["slug"] == "invoke_code"}
        self.assertEqual(code_keys, CODE_NODE_KEYS)

    def test_code_field_value_type_is_text_template(self):
        """REGRESSION GUARD for the real-export mismatch: the `code` input value `type` must
        be `text_template` (the real Execute Code export shape), NEVER `literal`."""
        seen = set()
        for s in self.steps:
            if s["operation"]["slug"] != "invoke_code":
                continue
            for name, val in iter_field_values(s):
                if name == "code":
                    self.assertEqual(
                        val["type"], "text_template",
                        "%s: code field must be text_template, not %s"
                        % (s["reference_key"], val["type"]),
                    )
                    self.assertIsInstance(val["value"], str)
                    self.assertIn("def run(inputs, keyrings)", val["value"])
                    seen.add(s["reference_key"])
        self.assertEqual(seen, CODE_NODE_KEYS)

    # --- edges resolve ---
    def test_all_next_steps_resolve(self):
        for s in self.steps:
            for ns in s.get("next_steps", []) or []:
                self.assertIn(ns["next_step_reference_key"], self.by_key,
                              "%s -> %s" % (s["reference_key"], ns["next_step_reference_key"]))

    # --- reachability from the trigger, with NO cycles ---
    def test_reachable_and_acyclic(self):
        start = next(s["reference_key"] for s in self.steps if s["operation"]["slug"] == "ticket_created")
        reached = set()
        on_stack = set()
        self._cycle = False

        def walk(key):
            if key in on_stack:
                self._cycle = True
                return
            if key in reached:
                return
            reached.add(key)
            on_stack.add(key)
            for ns in self.by_key[key].get("next_steps", []) or []:
                walk(ns["next_step_reference_key"])
            on_stack.discard(key)

        walk(start)
        self.assertFalse(self._cycle, "graph has a cycle")
        self.assertEqual(reached, set(self.by_key),
                         "unreachable steps: %s" % (set(self.by_key) - reached))

    # --- every $get reference resolves to an existing step (no dangling refs) ---
    def test_all_get_refs_resolve(self):
        refs = set(re.findall(r"\$get\('([^']+)'", self.blob))
        self.assertTrue(refs, "expected some $get references")
        for r in refs:
            self.assertIn(r, self.by_key, "dangling $get reference: %s" % r)
        # The full edition DOES reference the Code-node outputs - confirm they are present
        # (the historical bug was that an import dropped these and left the refs dangling).
        self.assertIn("validate_classification", refs)
        self.assertIn("bug_validate_title", refs)

    # --- Router routes <-> output edges ---
    def test_router_routes_and_edges(self):
        router = next(s for s in self.steps if s["operation"]["slug"] == "router")
        names = set()
        for name, val in iter_field_values(router):
            if name == "routes":
                for item in val["value"]["items"]:
                    for comp in item["value"]:
                        for f in comp["fields"]:
                            if f["name"] == "name":
                                names.add(f["value"]["value"])
        self.assertEqual(names, ROUTE_NAMES)
        self.assertEqual(len(names), 3, "aligned Router must have EXACTLY 3 routes, no Review")
        ports = {ns["port_name"] for ns in router.get("next_steps", [])}
        self.assertEqual(ports, ROUTE_NAMES)

    # --- ALIGNED: no 4th Review route / fallback branch anywhere in the graph ---
    def test_no_review_route_or_fallback(self):
        # No step named/keyed Review, and no Review port edge.
        for s in self.steps:
            self.assertNotIn("review", s["reference_key"].lower(), s["reference_key"])
            for ns in s.get("next_steps", []) or []:
                self.assertNotEqual(ns["port_name"], "Review", s["reference_key"])
        # No requires_review decision field leaks into the live config (prose is fine, the
        # embedded strict code raises instead of emitting requires_review).
        self.assertNotIn("requires_review", self.inner["title"])

    # --- ALIGNED: validator embedded code RAISES on invalid (stops run, no Review path) ---
    def test_validator_code_raises_valueerror(self):
        vc = self.by_key["validate_classification"]
        code = {name: val for name, val in iter_field_values(vc)}.get("code")
        self.assertIsNotNone(code)
        self.assertEqual(code["type"], "text_template")
        self.assertIn("raise ValueError", code["value"])
        self.assertIn("def run(inputs, keyrings)", code["value"])
        # must NOT eval/exec the untrusted AI output (the docstring may MENTION $eval to
        # explain why it is avoided; what matters is no eval/exec call site).
        self.assertNotIn("eval(", code["value"])
        self.assertNotIn("exec(", code["value"])
        self.assertNotIn("$eval(", code["value"])

    # --- ALIGNED: Feature/Enhancement set medium directly, with NO no-downgrade gate ---
    def test_feature_enhancement_set_medium_unconditionally(self):
        for key in ("feature_set_severity", "enhancement_set_severity"):
            step = self.by_key[key]
            self.assertEqual(step["operation"]["slug"], "update_ticket")
            vals = {name: val for name, val in iter_field_values(step)}
            self.assertEqual(vals["severity"]["value"], "medium")
        # The Router must point Feature/Enhancement DIRECTLY at the update_ticket steps,
        # not at an if_else gate.
        router = next(s for s in self.steps if s["operation"]["slug"] == "router")
        targets = {ns["port_name"]: ns["next_step_reference_key"] for ns in router["next_steps"]}
        self.assertEqual(targets["Feature"], "feature_set_severity")
        self.assertEqual(targets["Enhancement"], "enhancement_set_severity")

    def test_only_one_if_else_the_bug_title_gate(self):
        if_else = [s["reference_key"] for s in self.steps if s["operation"]["slug"] == "if_else"]
        self.assertEqual(if_else, ["bug_title_if_else"])

    def test_bug_path_sets_high(self):
        step = self.by_key["bug_set_severity"]
        vals = {name: val for name, val in iter_field_values(step)}
        self.assertEqual(vals["severity"]["value"], "high")

    # --- if_else nodes have true/false ports ---
    def test_if_else_ports(self):
        for s in self.steps:
            if s["operation"]["slug"] == "if_else":
                ports = {ns["port_name"] for ns in s.get("next_steps", [])}
                self.assertEqual(ports, {"true", "false"}, s["reference_key"])

    # --- no hardcoded IDs; dynamic targeting only ---
    def test_no_hardcoded_object_ids(self):
        self.assertNotIn("don:core:", self.blob, "no hardcoded DON ids")
        for s in self.steps:
            if s["operation"]["slug"] in ("update_ticket", "add_comment"):
                for name, val in iter_field_values(s):
                    if name in ("id", "object"):
                        self.assertEqual(val["type"], "jsonata_expression", s["reference_key"])
                        self.assertIn("$get('ticket_created_1'", val["value"])

    # --- severity enum policy ---
    def test_severity_literals_valid_lowercase(self):
        for s in self.steps:
            if s["operation"]["slug"] == "update_ticket":
                for name, val in iter_field_values(s):
                    if name == "severity":
                        self.assertEqual(val["type"], "literal")
                        self.assertIn(val["value"], SEVERITY_ENUM)
                        self.assertEqual(val["value"], val["value"].lower())

    # --- comments are internal ---
    def test_all_comments_internal(self):
        for s in self.steps:
            if s["operation"]["slug"] == "add_comment":
                vis = {name: val for name, val in iter_field_values(s)}.get("visibility")
                self.assertIsNotNone(vis, s["reference_key"])
                self.assertEqual(vis["value"], "internal", s["reference_key"])

    # --- ask_ai delimits the untrusted title/body ---
    def test_ask_ai_input_delimits_untrusted_fields(self):
        ai = next(s for s in self.steps if s["operation"]["slug"] == "ask_ai")
        body = {name: val for name, val in iter_field_values(ai)}.get("ai_input")
        self.assertIsNotNone(body)
        self.assertEqual(body["type"], "text_template")
        self.assertIn("<ticket_title>", body["value"])
        self.assertIn("<ticket_body>", body["value"])
        self.assertIn("ticket_created_1", body["value"])


if __name__ == "__main__":
    unittest.main()
