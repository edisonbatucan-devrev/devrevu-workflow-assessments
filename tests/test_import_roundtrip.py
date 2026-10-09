"""Unit tests for the import round-trip checker (check_import_roundtrip.py).

Standard-library only, fully synthetic templates (no internal docs / private files copied).
Covers:

  * a benign re-serialization (steps/edges/keys/fields REORDERED, positions and prose
    descriptions changed) still PASSES;
  * a dropped step is detected, AND the now-dangling $get reference that pointed at it is
    detected;
  * a changed edge target / port is detected (missing + extra edge);
  * a changed operation slug and a changed input field set are detected;
  * a changed embedded Execute Code body is detected as a signature change;
  * a duplicate reference key in the exported template is detected;
  * the wrapper ({"data": "<stringified inner>"}) and bare-inner forms both load;
  * dangling references inside router/if_else CONDITIONS (not just template bodies) are
    detected.
"""
import copy
import json
import os
import sys
import unittest

# The round-trip checker now lives at the repo-root tools/ directory (shared across parts).
HERE = os.path.dirname(os.path.abspath(__file__))
_TOOLS = os.path.abspath(os.path.join(HERE, "..", "tools"))
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

import check_import_roundtrip as chk  # noqa: E402


def inner_template():
    """A small, fully synthetic 4-step graph used as the EXPECTED baseline.

    trigger -> code_a -> router -> (hit) comment_hit / (miss) comment_miss
    The condition and the comment bodies reference code_a via $get, so dropping code_a
    produces dangling references the checker must catch.
    """
    return {
        "description": "synthetic",
        "serialization_version": {"major": 2, "minor": 0, "patch": 0},
        "title": "Synthetic",
        "steps": [
            {
                "name": "Trigger",
                "description": "start",
                "reference_key": "trigger",
                "operation": {"namespace": "devrev", "slug": "ticket_created"},
                "next_steps": [
                    {"port_name": "output", "next_step_reference_key": "code_a", "next_port_name": "input"}
                ],
                "ui_metadata": {"position": {"x": 0, "y": 0}},
            },
            {
                "name": "Code A",
                "description": "classify",
                "reference_key": "code_a",
                "operation": {"namespace": "devrev", "slug": "invoke_code"},
                "input_values": [
                    {
                        "fields": [
                            {"name": "code", "value": {"type": "literal", "value": "def run(i,k):\n    return {}\n"}},
                        ],
                        "port_name": "input",
                    }
                ],
                "next_steps": [
                    {"port_name": "output", "next_step_reference_key": "router", "next_port_name": "input"}
                ],
                "ui_metadata": {"position": {"x": 0, "y": 150}},
            },
            {
                "name": "Router",
                "description": "route",
                "reference_key": "router",
                "operation": {"namespace": "devrev", "slug": "router"},
                "input_values": [
                    {
                        "fields": [
                            {
                                "name": "routes",
                                "value": {
                                    "type": "literal",
                                    "value": {
                                        "conditions": [
                                            {
                                                "operands": [
                                                    {"type": "jsonata_expression", "value": "$get('code_a', 'output').ok"},
                                                    {"type": "literal", "value": [True]},
                                                ],
                                                "operator": "contains_any",
                                            }
                                        ]
                                    },
                                },
                            }
                        ],
                        "port_name": "input",
                    }
                ],
                "next_steps": [
                    {"port_name": "hit", "next_step_reference_key": "comment_hit", "next_port_name": "input"},
                    {"port_name": "miss", "next_step_reference_key": "comment_miss", "next_port_name": "input"},
                ],
                "ui_metadata": {"position": {"x": 0, "y": 300}},
            },
            {
                "name": "Comment hit",
                "description": "hit",
                "reference_key": "comment_hit",
                "operation": {"namespace": "devrev", "slug": "add_comment"},
                "input_values": [
                    {
                        "fields": [
                            {"name": "object", "value": {"type": "jsonata_expression", "value": "$get('trigger', 'output').id"}},
                            {"name": "body", "value": {"type": "text_template", "value": "A says {% expr $get('code_a', 'output').reason %}"}},
                        ],
                        "port_name": "input",
                    }
                ],
                "ui_metadata": {"position": {"x": -100, "y": 450}},
            },
            {
                "name": "Comment miss",
                "description": "miss",
                "reference_key": "comment_miss",
                "operation": {"namespace": "devrev", "slug": "add_comment"},
                "input_values": [
                    {
                        "fields": [
                            {"name": "object", "value": {"type": "jsonata_expression", "value": "$get('trigger', 'output').id"}},
                            {"name": "body", "value": {"type": "text_template", "value": "miss"}},
                        ],
                        "port_name": "input",
                    }
                ],
                "ui_metadata": {"position": {"x": 100, "y": 450}},
            },
        ],
    }


def wrap(inner):
    return {"data": json.dumps(inner), "templateVersion": "2.0.0"}


def run_report(expected_inner, exported_inner):
    return chk.compare(chk.collect(expected_inner), chk.collect(exported_inner))


class TestRoundtripChecker(unittest.TestCase):
    def test_identical_passes(self):
        exp = inner_template()
        rep = run_report(exp, copy.deepcopy(exp))
        self.assertTrue(rep["ok"], rep)

    def test_reorder_and_cosmetic_changes_pass(self):
        """Reordered steps, reordered edges/fields, changed positions and prose -> PASS."""
        exp = inner_template()
        got = copy.deepcopy(exp)
        got["steps"] = list(reversed(got["steps"]))  # reorder steps
        for s in got["steps"]:
            s["description"] = "COMPLETELY DIFFERENT PROSE"
            s.get("ui_metadata", {}).get("position", {}).update({"x": 999, "y": 999})
            # reorder edges where present
            if s.get("next_steps"):
                s["next_steps"] = list(reversed(s["next_steps"]))
            for grp in s.get("input_values", []) or []:
                grp["fields"] = list(reversed(grp["fields"]))
        rep = run_report(exp, got)
        self.assertTrue(rep["ok"], rep)

    def test_wrapper_and_bare_inner_both_load(self):
        exp = inner_template()
        wpath = os.path.join(HERE, "_tmp_wrap.json")
        bpath = os.path.join(HERE, "_tmp_bare.json")
        try:
            with open(wpath, "w", encoding="utf-8") as fh:
                json.dump(wrap(exp), fh)
            with open(bpath, "w", encoding="utf-8") as fh:
                json.dump(exp, fh)
            self.assertEqual(chk.load_inner(wpath)["steps"][0]["reference_key"], "trigger")
            self.assertEqual(chk.load_inner(bpath)["steps"][0]["reference_key"], "trigger")
        finally:
            for p in (wpath, bpath):
                if os.path.exists(p):
                    os.remove(p)

    def test_dropped_step_and_dangling_refs_detected(self):
        """Known-failed-export shape: drop code_a; its $get refs (in condition AND body)
        become dangling, and the edge into it is missing."""
        exp = inner_template()
        got = copy.deepcopy(exp)
        got["steps"] = [s for s in got["steps"] if s["reference_key"] != "code_a"]
        # rewire trigger straight to router so the only diff is the drop + dangling refs
        for s in got["steps"]:
            if s["reference_key"] == "trigger":
                s["next_steps"] = [
                    {"port_name": "output", "next_step_reference_key": "router", "next_port_name": "input"}
                ]
        rep = run_report(exp, got)
        self.assertFalse(rep["ok"])
        self.assertIn("code_a", rep["dropped_reference_keys"])
        dangling = {d["reference_key"] for d in rep["dangling_get_references"]}
        self.assertIn("code_a", dangling)  # referenced by router condition + comment body

    def test_changed_edge_target_and_port_detected(self):
        exp = inner_template()
        got = copy.deepcopy(exp)
        for s in got["steps"]:
            if s["reference_key"] == "router":
                # wrong target and wrong port on the "hit" edge
                s["next_steps"] = [
                    {"port_name": "hit", "next_step_reference_key": "comment_miss", "next_port_name": "wrong_port"},
                    {"port_name": "miss", "next_step_reference_key": "comment_miss", "next_port_name": "input"},
                ]
        rep = run_report(exp, got)
        self.assertFalse(rep["ok"])
        self.assertTrue(rep["missing_edges"])
        self.assertTrue(rep["extra_edges"])

    def test_changed_slug_detected(self):
        exp = inner_template()
        got = copy.deepcopy(exp)
        for s in got["steps"]:
            if s["reference_key"] == "code_a":
                s["operation"]["slug"] = "ask_ai"
        rep = run_report(exp, got)
        self.assertFalse(rep["ok"])
        changed = {c["reference_key"] for c in rep["changed_operation_signatures"]}
        self.assertIn("code_a", changed)

    def test_changed_input_fields_detected(self):
        exp = inner_template()
        got = copy.deepcopy(exp)
        for s in got["steps"]:
            if s["reference_key"] == "comment_hit":
                # drop the body field -> signature differs
                s["input_values"][0]["fields"] = [
                    f for f in s["input_values"][0]["fields"] if f["name"] != "body"
                ]
        rep = run_report(exp, got)
        self.assertFalse(rep["ok"])
        changed = {c["reference_key"] for c in rep["changed_operation_signatures"]}
        self.assertIn("comment_hit", changed)

    def test_changed_code_body_detected(self):
        exp = inner_template()
        got = copy.deepcopy(exp)
        for s in got["steps"]:
            if s["reference_key"] == "code_a":
                s["input_values"][0]["fields"][0]["value"]["value"] = "def run(i,k):\n    return {'x':1}\n"
        rep = run_report(exp, got)
        self.assertFalse(rep["ok"])
        changed = [c for c in rep["changed_operation_signatures"] if c["reference_key"] == "code_a"]
        self.assertTrue(changed and changed[0]["code_changed"])

    def test_changed_code_value_type_detected(self):
        """REGRESSION for the real-export mismatch: flipping the `code` field value `type`
        from `literal` to `text_template` (body byte-identical) must be caught as a changed
        signature flagged value_type_changed - NOT silently accepted."""
        exp = inner_template()
        got = copy.deepcopy(exp)
        for s in got["steps"]:
            if s["reference_key"] == "code_a":
                # same string body, only the value `type` changes
                s["input_values"][0]["fields"][0]["value"]["type"] = "text_template"
        rep = run_report(exp, got)
        self.assertFalse(rep["ok"])
        changed = [c for c in rep["changed_operation_signatures"] if c["reference_key"] == "code_a"]
        self.assertTrue(changed, rep)
        self.assertTrue(changed[0]["value_type_changed"])
        self.assertFalse(changed[0]["code_changed"], "body is identical; only the type flipped")

    def test_extra_and_duplicate_keys_detected(self):
        exp = inner_template()
        got = copy.deepcopy(exp)
        # add an unexpected extra step AND a duplicate of an existing key
        extra = copy.deepcopy(got["steps"][-1])
        extra["reference_key"] = "comment_extra"
        got["steps"].append(extra)
        dup = copy.deepcopy(got["steps"][0])
        got["steps"].append(dup)  # duplicate "trigger"
        rep = run_report(exp, got)
        self.assertFalse(rep["ok"])
        self.assertIn("comment_extra", rep["extra_reference_keys"])
        self.assertIn("trigger", rep["duplicate_reference_keys"])


if __name__ == "__main__":
    unittest.main()
