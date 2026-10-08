"""Structure unit tests for the corrected Part 2 exported workflow template.

Standard-library only. Validates the IMPORT-format artifact
`part2-ai-classify-router/templates/11-Part 2-template.json` without any DevRev API:

  * wrapper / serialization version are the genuine export shape;
  * the inner graph is reachable from the trigger with NO cycles;
  * every next_step reference resolves to a real step;
  * the Router has exactly the 4 named routes (Bug/Feature/Enhancement/Review) and each
    route name has a matching output edge (route name -> port -> edge);
  * node operation slugs are the known/verified set;
  * the Execute Code node bodies embedded as literals compile as Python and expose run();
  * dynamic targeting only - NO hardcoded DON/display IDs in any field value;
  * severity literals obey the lowercase enum policy.
"""
import ast
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PART2 = os.path.dirname(HERE)
TEMPLATE = os.path.join(PART2, "templates", "11-Part 2-template.json")

KNOWN_SLUGS = {
    "ticket_created", "ask_ai", "invoke_code", "router", "update_ticket",
    "add_comment", "if_else",
}
ROUTE_NAMES = {"Bug", "Feature", "Enhancement", "Review"}
SEVERITY_ENUM = {"high", "medium", "low", "blocker"}


def load_inner():
    with open(TEMPLATE, encoding="utf-8") as fh:
        wrapper = json.load(fh)
    return wrapper, json.loads(wrapper["data"])


def iter_field_values(node):
    """Yield every {type,value} value node across a step's input_values fields (shallow)."""
    for grp in node.get("input_values", []) or []:
        for f in grp.get("fields", []) or []:
            yield f.get("name"), f.get("value")


class TestPart2Template(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wrapper, cls.inner = load_inner()
        cls.steps = cls.inner["steps"]
        cls.by_key = {s["reference_key"]: s for s in cls.steps}

    # --- wrapper / version ---
    def test_wrapper_shape(self):
        self.assertEqual(self.wrapper["templateVersion"], "2.0.0")
        self.assertIsInstance(self.wrapper["data"], str)

    def test_serialization_version(self):
        self.assertEqual(self.inner["serialization_version"], {"major": 2, "minor": 0, "patch": 0})

    def test_title_is_part2(self):
        self.assertEqual(self.inner["title"], "Part 2")

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
        # Every step is reachable from the trigger.
        self.assertEqual(reached, set(self.by_key), "unreachable steps: %s" % (set(self.by_key) - reached))

    # --- Router routes <-> output edges ---
    def test_router_routes_and_edges(self):
        router = next(s for s in self.steps if s["operation"]["slug"] == "router")
        # collect declared route names
        names = set()
        for name, val in iter_field_values(router):
            if name == "routes":
                for item in val["value"]["items"]:
                    for comp in item["value"]:
                        for f in comp["fields"]:
                            if f["name"] == "name":
                                names.add(f["value"]["value"])
        self.assertEqual(names, ROUTE_NAMES)
        # each route name must have a matching output edge port
        ports = {ns["port_name"] for ns in router.get("next_steps", [])}
        self.assertEqual(ports, ROUTE_NAMES)

    def test_router_conditions_match_single_route_value(self):
        """Every route condition is a contains_any against the derived `route` field with a
        single-value literal list equal to the route name -> mutually exclusive by design."""
        router = next(s for s in self.steps if s["operation"]["slug"] == "router")
        seen = {}
        for name, val in iter_field_values(router):
            if name != "routes":
                continue
            for item in val["value"]["items"]:
                for comp in item["value"]:
                    fields = {f["name"]: f["value"] for f in comp["fields"]}
                    rname = fields["name"]["value"]
                    cond = fields["condition"]["value"]
                    rule = cond["conditions"][0]["conditions"][0]
                    self.assertEqual(rule["operator"], "contains_any")
                    expr_op, lit_op = rule["operands"]
                    self.assertIn("validate_classification", expr_op["value"])
                    self.assertIn(".route", expr_op["value"])
                    self.assertEqual(lit_op["value"], [rname])
                    seen[rname] = True
        self.assertEqual(set(seen), ROUTE_NAMES)

    # --- if_else nodes have true/false ports ---
    def test_if_else_ports(self):
        for s in self.steps:
            if s["operation"]["slug"] == "if_else":
                ports = {ns["port_name"] for ns in s.get("next_steps", [])}
                self.assertEqual(ports, {"true", "false"}, s["reference_key"])

    # --- no hardcoded IDs anywhere; dynamic targeting only ---
    def test_no_hardcoded_object_ids(self):
        blob = self.wrapper["data"]
        self.assertNotIn("don:core:", blob, "no hardcoded DON ids")
        # update_ticket / add_comment must target via jsonata expression, never a literal id
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

    # --- embedded Execute Code bodies compile and expose run() ---
    def test_invoke_code_bodies_compile(self):
        found = 0
        for s in self.steps:
            if s["operation"]["slug"] != "invoke_code":
                continue
            found += 1
            code_val = {name: val for name, val in iter_field_values(s)}.get("code")
            self.assertIsNotNone(code_val, s["reference_key"])
            self.assertEqual(code_val["type"], "literal")
            tree = ast.parse(code_val["value"])  # raises SyntaxError on bad code
            funcs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
            self.assertIn("run", funcs, s["reference_key"])
        self.assertEqual(found, 2, "expected exactly 2 Execute Code nodes")

    # --- invoke_code output_schema shape ---
    def test_invoke_code_output_schema_fields(self):
        for s in self.steps:
            if s["operation"]["slug"] != "invoke_code":
                continue
            os_val = {name: val for name, val in iter_field_values(s)}.get("output_schema")
            self.assertIsNotNone(os_val, s["reference_key"])
            self.assertEqual(os_val["type"], "literal")
            for f in os_val["value"]["fields"]:
                self.assertIn(f["field_type"], ("bool", "text"))
                self.assertIn("name", f)
                self.assertIn("description", f)
                self.assertIn("is_required", f)
                self.assertIn("is_filterable", f)

    # --- ask_ai carries the delimited untrusted title/body ---
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
