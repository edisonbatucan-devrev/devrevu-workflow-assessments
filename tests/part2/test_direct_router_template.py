"""Structure + regex-sample tests for the Part 2 DIRECT Ask AI -> Router template.

Standard-library only. Validates the IMPORT-format artifact
`part2-ai-classify-router/templates/11-Part 2-direct-router.template.json` WITHOUT any DevRev
API. This is the current Part 2 candidate: Ticket Created -> Ask AI -> Router (Bug/Feature/
Enhancement), with NO Execute Code steps - Bug-title validation is a JSONata `$match` regex in
a native condition.

What is asserted (local structure + Python equivalents of the regex samples):
  * genuine export wrapper / serialization version; title mentions the direct Router;
  * the graph is reachable from the trigger with NO cycles and every next_step resolves;
  * every `$get('<key>', ...)` reference points at an existing step (no dangling refs);
  * Ask AI is wired DIRECTLY to the Router (no invoke_code node, no validator references);
  * the Router has EXACTLY the 3 named routes (Bug/Feature/Enhancement) with matching ports;
  * Feature/Enhancement set severity medium; Bug sets high; severity literals are lowercase;
  * only one if_else (the Bug-title regex gate) with true/false ports;
  * all comments are internal; no hardcoded DON ids; Ask AI delimits the untrusted title/body;
  * the routing + Bug-title regex strings behave as intended on Python `re` samples.

NOT asserted: DevRev import, JSONata runtime behavior, or live execution. These are local,
static checks only.
"""
import json
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
TEMPLATE = os.path.join(
    REPO, "part2-ai-classify-router", "templates", "11-Part 2-direct-router.template.json"
)

ROUTE_NAMES = {"Bug", "Feature", "Enhancement"}
SEVERITY_ENUM = {"high", "medium", "low", "blocker"}
KNOWN_SLUGS = {"ticket_created", "ask_ai", "router", "update_ticket", "add_comment", "if_else"}


def load_inner():
    with open(TEMPLATE, encoding="utf-8") as fh:
        wrapper = json.load(fh)
    return wrapper, json.loads(wrapper["data"])


def iter_field_values(node):
    for grp in node.get("input_values", []) or []:
        for f in grp.get("fields", []) or []:
            yield f.get("name"), f.get("value")


class TestDirectRouterTemplate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wrapper, cls.inner = load_inner()
        cls.steps = cls.inner["steps"]
        cls.by_key = {s["reference_key"]: s for s in cls.steps}
        cls.blob = cls.wrapper["data"]

    def test_wrapper_shape(self):
        self.assertEqual(self.wrapper["templateVersion"], "2.0.0")
        self.assertIsInstance(self.wrapper["data"], str)

    def test_serialization_version(self):
        self.assertEqual(self.inner["serialization_version"], {"major": 2, "minor": 0, "patch": 0})

    def test_title_mentions_direct_router(self):
        self.assertIn("Router", self.inner["title"])

    def test_description_mentions_sandbox_filter(self):
        desc = self.inner["description"].lower()
        self.assertIn("sandbox", desc)
        self.assertIn("filter", desc)

    def test_known_slugs_only(self):
        for s in self.steps:
            self.assertIn(s["operation"]["slug"], KNOWN_SLUGS, s["reference_key"])
            self.assertEqual(s["operation"]["namespace"], "devrev")

    def test_no_invoke_code_or_validator_references(self):
        for s in self.steps:
            self.assertNotEqual(s["operation"]["slug"], "invoke_code", s["reference_key"])
        self.assertNotIn("validate_classification", self.blob)
        self.assertNotIn("bug_validate_title", self.blob)

    def test_exactly_one_trigger(self):
        triggers = [s for s in self.steps if s["operation"]["slug"] == "ticket_created"]
        self.assertEqual(len(triggers), 1)

    def test_unique_reference_keys(self):
        keys = [s["reference_key"] for s in self.steps]
        self.assertEqual(len(keys), len(set(keys)))

    def test_all_next_steps_resolve(self):
        for s in self.steps:
            for ns in s.get("next_steps", []) or []:
                self.assertIn(ns["next_step_reference_key"], self.by_key,
                              "%s -> %s" % (s["reference_key"], ns["next_step_reference_key"]))

    def test_reachable_and_acyclic(self):
        start = next(s["reference_key"] for s in self.steps
                     if s["operation"]["slug"] == "ticket_created")
        reached, on_stack = set(), set()
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

    def test_all_get_refs_resolve(self):
        refs = set(re.findall(r"\$get\('([^']+)'", self.blob))
        self.assertTrue(refs, "expected some $get references")
        for r in refs:
            self.assertIn(r, self.by_key, "dangling $get reference: %s" % r)

    def test_ask_ai_connects_directly_to_router(self):
        ai = next(s for s in self.steps if s["operation"]["slug"] == "ask_ai")
        router = next(s for s in self.steps if s["operation"]["slug"] == "router")
        targets = {ns["next_step_reference_key"] for ns in ai.get("next_steps", [])}
        self.assertIn(router["reference_key"], targets)

    def test_router_routes_and_ports(self):
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
        ports = {ns["port_name"] for ns in router.get("next_steps", [])}
        self.assertEqual(ports, ROUTE_NAMES)

    def test_only_one_if_else_with_true_false_ports(self):
        if_else = [s for s in self.steps if s["operation"]["slug"] == "if_else"]
        self.assertEqual(len(if_else), 1)
        ports = {ns["port_name"] for ns in if_else[0].get("next_steps", [])}
        self.assertEqual(ports, {"true", "false"})

    def test_severity_literals_valid_lowercase(self):
        seen = {}
        for s in self.steps:
            if s["operation"]["slug"] == "update_ticket":
                for name, val in iter_field_values(s):
                    if name == "severity":
                        self.assertEqual(val["type"], "literal")
                        self.assertIn(val["value"], SEVERITY_ENUM)
                        self.assertEqual(val["value"], val["value"].lower())
                        seen[s["reference_key"]] = val["value"]
        # Bug sets high; the other two update_ticket steps set medium.
        self.assertIn("high", seen.values())
        self.assertEqual(sum(1 for v in seen.values() if v == "medium"), 2)

    def test_all_comments_internal(self):
        found = False
        for s in self.steps:
            if s["operation"]["slug"] == "add_comment":
                found = True
                vis = {name: val for name, val in iter_field_values(s)}.get("visibility")
                self.assertIsNotNone(vis, s["reference_key"])
                self.assertEqual(vis["value"], "internal", s["reference_key"])
        self.assertTrue(found)

    def test_no_hardcoded_object_ids(self):
        self.assertNotIn("don:core:", self.blob, "no hardcoded DON ids")
        for s in self.steps:
            if s["operation"]["slug"] in ("update_ticket", "add_comment"):
                for name, val in iter_field_values(s):
                    if name in ("id", "object"):
                        self.assertEqual(val["type"], "jsonata_expression", s["reference_key"])
                        self.assertIn("$get('ticket_created_1'", val["value"])

    def test_ask_ai_delimits_untrusted_fields(self):
        ai = next(s for s in self.steps if s["operation"]["slug"] == "ask_ai")
        body = {name: val for name, val in iter_field_values(ai)}.get("ai_input")
        self.assertIsNotNone(body)
        self.assertEqual(body["type"], "text_template")
        self.assertIn("<ticket_title>", body["value"])
        self.assertIn("<ticket_body>", body["value"])
        self.assertIn("ticket_created_1", body["value"])


class TestRegexSamples(unittest.TestCase):
    """Python equivalents of the JSONata $match regexes the template relies on.

    These prove the INTENT of the patterns on sample strings. They do NOT execute DevRev's
    JSONata runtime - route evaluation in the live builder is unverified.
    """

    # Route match: a category line, then a single Justification line (1-1000 chars).
    ROUTE_RE = {
        "Bug": re.compile(r"^Bug\r?\nJustification: [^\r\n]{1,1000}\r?\n?$"),
        "Feature": re.compile(r"^Feature\r?\nJustification: [^\r\n]{1,1000}\r?\n?$"),
        "Enhancement": re.compile(r"^Enhancement\r?\nJustification: [^\r\n]{1,1000}\r?\n?$"),
    }
    TITLE_RE = re.compile(r"^\[BUG\] .{5,120}$")

    def test_route_regex_accepts_well_formed_output(self):
        self.assertTrue(self.ROUTE_RE["Bug"].match("Bug\nJustification: Existing login breaks."))
        self.assertTrue(self.ROUTE_RE["Feature"].match(
            "Feature\nJustification: Brand-new capability."))
        self.assertTrue(self.ROUTE_RE["Enhancement"].match(
            "Enhancement\nJustification: Improves existing search."))

    def test_route_regex_is_category_specific(self):
        # A Feature-labelled output must NOT match the Bug route.
        self.assertIsNone(self.ROUTE_RE["Bug"].match(
            "Feature\nJustification: Brand-new capability."))

    def test_route_regex_rejects_malformed_output(self):
        for bad in ("", "Bug", "Bug\nno justification line", "garbage",
                    "Bug\nJustification: "):
            self.assertIsNone(self.ROUTE_RE["Bug"].match(bad), bad)

    def test_bug_title_regex(self):
        self.assertTrue(self.TITLE_RE.match("[BUG] Export crashes on 2MB file"))
        self.assertIsNone(self.TITLE_RE.match("Export crashes"))      # missing prefix
        self.assertIsNone(self.TITLE_RE.match("[BUG] abc"))           # under 5 chars after prefix
        self.assertIsNone(self.TITLE_RE.match("[BUG] " + "x" * 121))  # over 120 chars


if __name__ == "__main__":
    unittest.main()
