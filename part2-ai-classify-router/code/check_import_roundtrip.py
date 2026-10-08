#!/usr/bin/env python3
"""Import round-trip checker for DevRev workflow export templates.

Standard-library only. Compares an EXPECTED workflow template against the template
EXPORTED-AFTER-IMPORT and fails (exit code 1) if the import lost or changed anything that
matters for the graph's behavior:

  * dropped / extra / duplicate step reference keys;
  * changed operation signatures (namespace/slug, or the set of configured input field
    names on a step);
  * missing / changed / extra edges (next_step connections), compared as
    source_key:port -> target_key:port triples;
  * dangling `$get('<ref>', '<port>')` references - in jsonata_expression values, in
    text_template bodies, AND inside router / if_else conditions - that point at a
    reference key which no longer exists in the exported template.

What it deliberately IGNORES (so a benign re-serialization still passes):

  * step ORDER and the ORDER of edges / keys / input fields;
  * `ui_metadata` / canvas positions;
  * prose `description` fields on steps and routes;
  * exact whitespace of serialized JSON.

What it DOES compare exactly: because the task requires it, the embedded Execute Code
(`invoke_code`) node bodies are compared byte-for-byte (after structural extraction). A
changed `code` body is reported as a changed input signature / value mismatch.

It ALSO compares the VALUE TYPE of every configured input field (e.g. `literal` vs
`text_template` vs `jsonata_expression`). This catches an import silently rewriting a field's
value type even when the string body is unchanged - in particular an Execute Code `code`
field flipping between `literal` and `text_template` (the real-export mismatch this tooling
was built to catch); such a change is flagged `[VALUE TYPE CHANGED]`.

Both inputs may be either the genuine export WRAPPER
(`{"data": "<stringified inner JSON>", "templateVersion": "..."}`) or a bare inner template
object (`{"steps": [...], ...}`); the wrapper's stringified `data` body is decoded
automatically.

NOTE: this is a LOCAL structural check. It does NOT simulate the DevRev importer and is NOT
evidence of live import compatibility. A clean result means the two files describe the same
graph; a failing result is concrete evidence that the import changed the graph.

Usage:
    python3 check_import_roundtrip.py EXPECTED.json EXPORTED_AFTER_IMPORT.json
    python3 check_import_roundtrip.py EXPECTED.json EXPORTED.json --report out.json

Exit code 0 = round-trip preserved; 1 = differences found; 2 = bad input/usage.
"""

import argparse
import json
import re
import sys


# Matches $get('ref_key', 'port') / $get("ref_key","port") with flexible spacing/quoting.
_GET_RE = re.compile(
    r"""\$get\(\s*(['"])(?P<ref>.*?)\1\s*,\s*(['"])(?P<port>.*?)\3\s*\)"""
)


def load_inner(path):
    """Load a template file and return its inner graph object.

    Accepts the export wrapper ({"data": "<json string>", ...}) or a bare inner object.
    Raises ValueError with a clear message on anything unparseable.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, ValueError) as e:
        raise ValueError("could not read/parse %s: %s" % (path, e))
    inner = raw
    if isinstance(raw, dict) and isinstance(raw.get("data"), str):
        try:
            inner = json.loads(raw["data"])
        except ValueError as e:
            raise ValueError("could not parse stringified `data` body of %s: %s" % (path, e))
    if not isinstance(inner, dict) or not isinstance(inner.get("steps"), list):
        raise ValueError("%s does not look like a workflow template (no steps[])" % path)
    return inner


def _walk_values(value, found):
    """Recurse through a step input `value` dict collecting $get references and code.

    `found` is a dict with keys:
      - 'refs': set of (ref, port) tuples referenced anywhere via $get(...)
    We scan every string we encounter (jsonata_expression values, text_template bodies, and
    any literal strings such as condition operands), so references inside router/if_else
    conditions are covered too.
    """
    if isinstance(value, dict):
        for v in value.values():
            _walk_values(v, found)
    elif isinstance(value, list):
        for v in value:
            _walk_values(v, found)
    elif isinstance(value, str):
        for m in _GET_RE.finditer(value):
            found["refs"].add((m.group("ref"), m.group("port")))


def input_field_names(step):
    """Return the sorted tuple of configured input field names across all input groups.

    This is the step's input *signature* - which fields are set - independent of ordering.
    """
    names = []
    for grp in step.get("input_values", []) or []:
        for f in grp.get("fields", []) or []:
            n = f.get("name")
            if n is not None:
                names.append(n)
    return tuple(sorted(names))


def code_literals(step):
    """Return the sorted tuple of embedded Execute Code `code` bodies on a step.

    Compared exactly (byte-for-byte) so a changed node body surfaces as a signature change.
    (Covers any value type - the `code` input may legitimately be a `text_template`, which is
    the real Execute Code export shape; this still extracts the string body.)
    """
    bodies = []
    for grp in step.get("input_values", []) or []:
        for f in grp.get("fields", []) or []:
            if f.get("name") == "code":
                val = f.get("value") or {}
                if isinstance(val, dict) and isinstance(val.get("value"), str):
                    bodies.append(val["value"])
    return tuple(sorted(bodies))


def field_value_types(step):
    """Return the sorted tuple of (field_name, value_type) pairs for a step's input fields.

    This preserves the VALUE TYPE of each configured input (e.g. `literal`, `text_template`,
    `jsonata_expression`, `list_value`). It is deliberately part of the operation signature so
    that an import silently rewriting a field's value type - in particular an Execute Code
    `code` field flipping between `literal` and `text_template` (the real-export mismatch this
    repair fixed) - is caught as a changed signature, even when the string body is unchanged.
    """
    pairs = []
    for grp in step.get("input_values", []) or []:
        for f in grp.get("fields", []) or []:
            name = f.get("name")
            val = f.get("value") or {}
            vtype = val.get("type") if isinstance(val, dict) else None
            if name is not None:
                pairs.append((name, vtype))
    return tuple(sorted(pairs))


def edges(step):
    """Return the set of outgoing edge triples for a step.

    Each triple: (source_port, target_reference_key, target_port). Order-independent.
    """
    out = set()
    for ns in step.get("next_steps", []) or []:
        out.add(
            (
                ns.get("port_name"),
                ns.get("next_step_reference_key"),
                ns.get("next_port_name"),
            )
        )
    return out


def collect(inner):
    """Build the semantic model used for comparison.

    Returns a dict:
      keys_in_order   : list of reference_key in file order (to detect duplicates)
      signatures      : {ref_key: (namespace, slug, input_field_names, code_literals,
                        field_value_types)}
      edges           : set of (src_key, src_port, tgt_key, tgt_port)
      get_refs        : set of (ref, port) referenced via $get anywhere
    """
    keys_in_order = []
    signatures = {}
    all_edges = set()
    get_refs = {"refs": set()}
    for step in inner["steps"]:
        key = step.get("reference_key")
        keys_in_order.append(key)
        op = step.get("operation") or {}
        signatures[key] = (
            op.get("namespace"),
            op.get("slug"),
            input_field_names(step),
            code_literals(step),
            field_value_types(step),
        )
        for src_port, tgt_key, tgt_port in edges(step):
            all_edges.add((key, src_port, tgt_key, tgt_port))
        for grp in step.get("input_values", []) or []:
            for f in grp.get("fields", []) or []:
                _walk_values(f.get("value"), get_refs)
    return {
        "keys_in_order": keys_in_order,
        "signatures": signatures,
        "edges": all_edges,
        "get_refs": get_refs["refs"],
    }


def compare(expected, exported):
    """Compare two collected models. Returns a report dict with a top-level `ok` bool."""
    report = {
        "ok": True,
        "dropped_reference_keys": [],
        "extra_reference_keys": [],
        "duplicate_reference_keys": [],
        "changed_operation_signatures": [],
        "missing_edges": [],
        "extra_edges": [],
        "dangling_get_references": [],
    }

    exp_keys = [k for k in expected["keys_in_order"] if k is not None]
    exported_keys = [k for k in exported["keys_in_order"] if k is not None]
    exp_set = set(exp_keys)
    exported_set = set(exported_keys)

    # Duplicate reference keys within the EXPORTED template.
    seen = set()
    dups = set()
    for k in exported_keys:
        if k in seen:
            dups.add(k)
        seen.add(k)
    report["duplicate_reference_keys"] = sorted(dups)

    report["dropped_reference_keys"] = sorted(exp_set - exported_set)
    report["extra_reference_keys"] = sorted(exported_set - exp_set)

    # Operation signatures for keys present in BOTH (drops are reported separately above).
    for key in sorted(exp_set & exported_set):
        exp_sig = expected["signatures"][key]
        got_sig = exported["signatures"][key]
        if exp_sig != got_sig:
            report["changed_operation_signatures"].append(
                {
                    "reference_key": key,
                    "expected": {
                        "namespace": exp_sig[0],
                        "slug": exp_sig[1],
                        "input_fields": list(exp_sig[2]),
                        "code_bodies_count": len(exp_sig[3]),
                        "field_value_types": [list(p) for p in exp_sig[4]],
                    },
                    "exported": {
                        "namespace": got_sig[0],
                        "slug": got_sig[1],
                        "input_fields": list(got_sig[2]),
                        "code_bodies_count": len(got_sig[3]),
                        "field_value_types": [list(p) for p in got_sig[4]],
                    },
                    "code_changed": exp_sig[3] != got_sig[3],
                    "value_type_changed": exp_sig[4] != got_sig[4],
                }
            )

    # Edges (order-independent set comparison).
    def fmt_edge(e):
        return {"from": e[0], "from_port": e[1], "to": e[2], "to_port": e[3]}

    missing = expected["edges"] - exported["edges"]
    extra = exported["edges"] - expected["edges"]
    report["missing_edges"] = [fmt_edge(e) for e in sorted(missing)]
    report["extra_edges"] = [fmt_edge(e) for e in sorted(extra)]

    # Dangling $get references: a reference in the EXPORTED template that points at a
    # reference key not present in the EXPORTED template.
    dangling = sorted(
        {ref for (ref, _port) in exported["get_refs"] if ref not in exported_set}
    )
    report["dangling_get_references"] = [
        {"reference_key": ref, "ports": sorted(p for (r, p) in exported["get_refs"] if r == ref)}
        for ref in dangling
    ]

    report["ok"] = not (
        report["dropped_reference_keys"]
        or report["extra_reference_keys"]
        or report["duplicate_reference_keys"]
        or report["changed_operation_signatures"]
        or report["missing_edges"]
        or report["extra_edges"]
        or report["dangling_get_references"]
    )
    return report


def print_report(report, expected_path, exported_path):
    print("Import round-trip check")
    print("  expected : %s" % expected_path)
    print("  exported : %s" % exported_path)
    print("")

    def section(title, items, fmt):
        if items:
            print("FAIL %s (%d):" % (title, len(items)))
            for it in items:
                print("    - %s" % fmt(it))

    section("dropped reference keys", report["dropped_reference_keys"], str)
    section("extra reference keys", report["extra_reference_keys"], str)
    section("duplicate reference keys", report["duplicate_reference_keys"], str)
    section(
        "changed operation signatures",
        report["changed_operation_signatures"],
        lambda it: "%s: %s/%s fields=%s%s%s"
        % (
            it["reference_key"],
            it["exported"]["namespace"],
            it["exported"]["slug"],
            it["exported"]["input_fields"],
            " [CODE CHANGED]" if it["code_changed"] else "",
            " [VALUE TYPE CHANGED]" if it.get("value_type_changed") else "",
        ),
    )
    section(
        "missing edges",
        report["missing_edges"],
        lambda e: "%s[%s] -> %s[%s]" % (e["from"], e["from_port"], e["to"], e["to_port"]),
    )
    section(
        "extra edges",
        report["extra_edges"],
        lambda e: "%s[%s] -> %s[%s]" % (e["from"], e["from_port"], e["to"], e["to_port"]),
    )
    section(
        "dangling $get references",
        report["dangling_get_references"],
        lambda it: "$get('%s', ...) ports=%s - target no longer exists"
        % (it["reference_key"], it["ports"]),
    )

    print("")
    print("RESULT:", "PASS - round-trip preserved" if report["ok"] else "FAIL - import changed the graph")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Fail if a workflow export lost/changed steps, edges, signatures, or refs."
    )
    parser.add_argument("expected", help="path to the EXPECTED template (wrapper or inner)")
    parser.add_argument("exported", help="path to the EXPORTED-after-import template")
    parser.add_argument("--report", help="optional path to write the JSON diff report")
    args = parser.parse_args(argv)

    try:
        expected_inner = load_inner(args.expected)
        exported_inner = load_inner(args.exported)
    except ValueError as e:
        print("ERROR:", e, file=sys.stderr)
        return 2

    report = compare(collect(expected_inner), collect(exported_inner))
    report["expected_path"] = args.expected
    report["exported_path"] = args.exported

    print_report(report, args.expected, args.exported)

    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, sort_keys=True)
            fh.write("\n")
        print("Wrote report:", args.report)

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
