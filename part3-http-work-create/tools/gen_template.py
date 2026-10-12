#!/usr/bin/env python3
"""Deterministically generate the Part 3 importable workflow template (v2 serialization).

GROUNDED, NOT fabricated. Every node shape here is copied from the PUBLIC
shashankcube/computer-skill create-workflow-template v2 examples + operation schemas:
  - envelope {"data": <stringified inner>, "templateVersion": "2.0.0"} and inner
    serialization_version {major:2} + steps[] + title          : working-invoke-code-sample.json
  - invoke_code input_ports / input_values(code=text_template, input_values=
    list_value>composite_value_list name/value, output_schema=literal fields) /
    output_ports                                                 : operations/schemas/invoke_code.md
  - http (auth_type=Bearer literal, url/body=text_template, method literal, headers
    composite pair array, enable_retries=false) + output status_code/body            : working-csat-score-on-ticket-resolved.json http_1
  - add_comment (object id, visibility literal internal, body text_template)          : working-csat-score-on-ticket-resolved.json add_comment_1
  - if_else (condition literal group>group>rule; true/false/error output ports)       : working-csat-score-on-ticket-resolved.json if_else_1
  - send_notification (receivers list_value>literal [DON], title/body rich_text)      : working-loop-variable-sample.json send_notification_1
  - ticket trigger fields_to_watch / owned_by[]/applies_to_part/severity shapes       : operations/schemas/ticket_created.md

This is an IMPORT DRAFT. The HTTP auth connection is selected in the UI AFTER import
(no raw token is serialized). Live import/run remains UNVERIFIED.

Usage:  python3 gen_template.py <out1.json> [<out2.json> ...]
"""

import json
import os
import sys

HERE = os.path.abspath(os.path.dirname(__file__))
CODE_DIR = os.path.abspath(os.path.join(HERE, "..", "code"))

WORKS_CREATE_URL = "https://api.devrev.ai/works.create"


# ---------------------------------------------------------------------------
# Embedded Execute Code bodies.
#
# Each wrapper imports NOTHING from disk (invoke_code sandbox has no repo files);
# the original tested logic is pasted inline and the original run(...) is renamed
# locally (e.g. _run_core) so the on-disk helper modules are untouched. Short, clear
# TOP guard constants are mandatory and contain NO secrets.
# ---------------------------------------------------------------------------

BUILD_REQUEST_CODE = r'''# Part 3 - build_request (Execute Code). GROUNDED wrapper around the tested
# part3-http-work-create/code/build_request.py core; adds a DEFAULT-SAFE preflight.
#
# ===== MANDATORY SAFETY GUARDS (set these in the UI before you publish) =====
# No secret belongs in these constants. They gate LIVE creation only.
ALLOW_LIVE_CREATE = False          # must be flipped to True to allow the HTTP create
EXPECTED_PART_ID = ''              # your dedicated sandbox Part 3 part DON (exact)
EXPECTED_TEST_OWNER_ID = ''        # YOUR own sandbox user DON (the test owner)
# ============================================================================

import json

MAX_TITLE_LEN = 256
WORKS_CREATE_URL = "https://api.devrev.ai/works.create"
_ALLOWED_HOSTS = ("api.devrev.ai",)


def _nonempty_str(v):
    return isinstance(v, str) and v.strip() != ""


def validate_endpoint(url):
    if not _nonempty_str(url):
        raise ValueError("endpoint URL is required")
    u = url.strip()
    if not u.startswith("https://"):
        raise ValueError("endpoint must use HTTPS (http:// and other schemes are rejected)")
    rest = u[len("https://"):]
    host = rest.split("/", 1)[0].split("?", 1)[0].split("@")[-1].split(":")[0].lower()
    if host not in _ALLOWED_HOSTS:
        raise ValueError("endpoint host is not an allow-listed DevRev host")
    if u != WORKS_CREATE_URL:
        raise ValueError("endpoint must be exactly %s (no alternate path/query/credentials)" % WORKS_CREATE_URL)
    return u


def _check_owner_ids(owned_by_ids):
    if not isinstance(owned_by_ids, (list, tuple)) or len(owned_by_ids) == 0:
        raise ValueError("owned_by_ids must be a non-empty list of user DONs")
    cleaned = []
    for owner in owned_by_ids:
        if not _nonempty_str(owner):
            raise ValueError("every owner id must be a non-empty string DON")
        cleaned.append(owner.strip())
    return cleaned


def build_works_create_body(ticket_id, title, applies_to_part_id, owned_by_ids, severity, expected_org_id=None):
    if not _nonempty_str(title):
        raise ValueError("title is required and must be a non-empty string")
    normalized_title = title.strip()
    if len(normalized_title) > MAX_TITLE_LEN:
        raise ValueError("title exceeds the maximum of %d characters" % MAX_TITLE_LEN)
    if not _nonempty_str(applies_to_part_id):
        raise ValueError("applies_to_part_id is required and must be a non-empty string")
    owners = _check_owner_ids(owned_by_ids)
    part = applies_to_part_id.strip()
    if expected_org_id is not None:
        if not _nonempty_str(expected_org_id):
            raise ValueError("expected_org_id, when provided, must be a non-empty string (no default)")
        org = expected_org_id.strip()
        for don in [part] + owners:
            if don.startswith("don:") and (org not in don):
                raise ValueError("a provided DON is not consistent with expected_org_id")
    external_ref = "devrevu-p3:" + str(ticket_id)
    payload = {
        "type": "issue",
        "title": normalized_title,
        "applies_to_part": part,
        "owned_by": owners,
        "body": "Auto-created from DevRevU Part 3 workflow for a 'low' severity ticket (synthetic reference).",
        "external_ref": external_ref,
    }
    return json.dumps(payload, separators=(",", ":")), external_ref


def _preflight(inputs):
    """DEFAULT-SAFE gate. Raises BEFORE the HTTP node unless the operator has explicitly
    opted a single test ticket in. Prevents a published workflow from creating issues for
    EVERY low-severity ticket. No secret is checked here."""
    sev = (inputs.get("severity") or "").strip().lower()
    part = (inputs.get("applies_to_part_id") or "").strip()
    owners = inputs.get("owned_by_ids") or []
    if not ALLOW_LIVE_CREATE:
        raise ValueError(
            "LIVE create is disabled by default. Set ALLOW_LIVE_CREATE=True in this node "
            "ONLY for a single sandbox test ticket, after setting EXPECTED_PART_ID and "
            "EXPECTED_TEST_OWNER_ID.")
    if sev != "low":
        raise ValueError("preflight: severity is not 'low'; refusing to create.")
    if not EXPECTED_PART_ID or part != EXPECTED_PART_ID:
        raise ValueError("preflight: ticket part does not match EXPECTED_PART_ID; refusing to create.")
    if not EXPECTED_TEST_OWNER_ID or EXPECTED_TEST_OWNER_ID not in owners:
        raise ValueError("preflight: ticket owner does not match EXPECTED_TEST_OWNER_ID; refusing to create.")


def run(inputs):
    inputs = inputs or {}
    endpoint = validate_endpoint(inputs.get("endpoint", WORKS_CREATE_URL))
    _preflight(inputs)
    body, external_ref = build_works_create_body(
        ticket_id=inputs.get("ticket_id", ""),
        title=inputs.get("title"),
        applies_to_part_id=inputs.get("applies_to_part_id"),
        owned_by_ids=inputs.get("owned_by_ids"),
        severity=inputs.get("severity", ""),
        expected_org_id=inputs.get("expected_org_id"),
    )
    return {"body": body, "external_ref": external_ref, "endpoint": endpoint}
'''

VALIDATE_RESPONSE_CODE = r'''# Part 3 - validate_response (Execute Code). GROUNDED copy of the tested
# part3-http-work-create/code/validate_response.py core. Raises on non-2xx / missing ids
# so a bad HTTP finish is a FAILED run. Never leaks the body or any token.
import json


class WorksCreateError(Exception):
    def __init__(self, message, code="non_2xx"):
        super().__init__(message)
        self.code = code


def _coerce_json(response_body):
    if isinstance(response_body, dict):
        return response_body
    if isinstance(response_body, str) and response_body.strip():
        try:
            return json.loads(response_body)
        except (ValueError, TypeError):
            raise WorksCreateError("Response body was not valid JSON.", code="bad_response")
    raise WorksCreateError("Response body was empty or of an unexpected type.", code="bad_response")


def validate_works_create(status_code, response_body):
    try:
        code = int(status_code)
    except (TypeError, ValueError):
        raise WorksCreateError("Missing or non-numeric HTTP status code.", code="bad_status")
    if code == 429:
        raise WorksCreateError("works.create was rate limited (429). Do not blindly retry in-node.", code="rate_limited")
    if code == 409:
        raise WorksCreateError("works.create returned a conflict (409); an issue may already exist.", code="conflict")
    if code < 200 or code >= 300:
        raise WorksCreateError("works.create returned non-2xx status %d." % code, code="non_2xx")
    data = _coerce_json(response_body)
    # Accept {"work": {...}} or a top-level shape. VERIFY the real path in the sandbox.
    work = data.get("work") if isinstance(data.get("work"), dict) else data
    work_id = work.get("id") if isinstance(work, dict) else None
    display_id = work.get("display_id") if isinstance(work, dict) else None
    if not work_id or not display_id:
        raise WorksCreateError("works.create succeeded (2xx) but response was missing work.id or work.display_id.", code="bad_response")
    return {"work_id": work_id, "display_id": display_id}


def run(inputs):
    inputs = inputs or {}
    return validate_works_create(inputs.get("status_code"), inputs.get("response_body"))
'''

REVERSE_SEVERITY_CODE = r'''# Part 3 - reverse_severity (Execute Code). GROUNDED copy of the tested
# part3-http-work-create/code/reverse_severity.py core.
VALID_SEVERITIES = ("low", "high", "medium", "blocker")


def reverse_severity(severity):
    if not isinstance(severity, str):
        raise ValueError("severity must be a string")
    normalized = severity.strip().lower()
    if normalized not in VALID_SEVERITIES:
        raise ValueError("severity must be one of %s" % ", ".join(VALID_SEVERITIES))
    return {"reversed": normalized[::-1], "original": normalized}


def run(inputs):
    inputs = inputs or {}
    return reverse_severity(inputs.get("severity"))
'''

NOTIFY_POLICY_CODE = r'''# Part 3 - notify_policy (Execute Code). GROUNDED wrapper around the tested
# part3-http-work-create/code/notify_policy.py core. DEFAULT-SAFE: should_notify is False
# unless the operator explicitly opts in AND the ticket owner matches the fixed test owner.
# This node PLANS the notification; it performs NO network call. The downstream native
# if_else gate (should_notify == true) is what actually guards send_notification.
#
# ===== MANDATORY SAFETY GUARDS (set in the UI before you publish) =====
ALLOW_OWNER_NOTIFICATION = False   # must be True to allow a real notification
EXPECTED_TEST_OWNER_ID = ''        # YOUR own sandbox user DON (the only allowed recipient)
# ======================================================================


class NotifyGateError(Exception):
    pass


def _nonempty_str(v):
    return isinstance(v, str) and v.strip() != ""


def plan_post_create_actions(create_result, reversed_severity, ticket_owner_id):
    if not isinstance(create_result, dict):
        raise NotifyGateError("No verified issue: refusing to notify (would risk a duplicate create).")
    work_id = create_result.get("work_id")
    display_id = create_result.get("display_id")
    if not _nonempty_str(work_id) or not _nonempty_str(display_id):
        raise NotifyGateError("Issue create did not return both work_id and display_id; not notifying.")
    if not _nonempty_str(reversed_severity):
        raise NotifyGateError("Missing reversed severity for the issue comment.")
    if not _nonempty_str(ticket_owner_id):
        raise NotifyGateError("Missing ticket owner id for the notification.")
    notification = "%s has been created for your ticket." % display_id
    issue_comment = "Reversed ticket severity: %s" % reversed_severity.strip()
    # DEFAULT-SAFE gate: off unless explicitly enabled AND recipient is the fixed test owner.
    should_notify = bool(
        ALLOW_OWNER_NOTIFICATION
        and _nonempty_str(EXPECTED_TEST_OWNER_ID)
        and ticket_owner_id.strip() == EXPECTED_TEST_OWNER_ID.strip()
    )
    return {
        "should_notify": should_notify,
        "work_id": work_id,
        "display_id": display_id,
        "issue_comment": issue_comment,
        "notification": notification,
    }


def run(inputs):
    inputs = inputs or {}
    create_result = inputs.get("create_result")
    if create_result is None:
        create_result = {
            "work_id": inputs.get("work_id"),
            "display_id": inputs.get("display_id"),
        }
    return plan_post_create_actions(
        create_result,
        inputs.get("reversed_severity"),
        inputs.get("ticket_owner_id"),
    )
'''


# ---------------------------------------------------------------------------
# Reusable serialization fragments (verbatim shapes from the public examples).
# ---------------------------------------------------------------------------

def _error_output_port():
    return {
        "name": "error",
        "schema": {"field_descriptors": [
            {"field_type": "text", "data_name": "message", "db_name": "message",
             "description": "Error message with more details about the error", "name": "message",
             "oasis": {"name": "message"}, "ui": {"display_name": "Error Message"}},
            {"field_type": "enum", "allowed_values": ["bad_request", "not_found", "internal"],
             "data_name": "type", "db_name": "type", "description": "Type of the error", "name": "type",
             "oasis": {"name": "type"}, "ui": {"display_name": "Error Type"}},
        ], "type": "field_descriptor"},
        "type": "error",
    }


def _invoke_code_input_port():
    return {
        "name": "input",
        "schema": {
            "composite_schemas": [{
                "description": "A variable",
                "fields": [
                    {"field_type": "tokens", "data_name": "name", "db_name": "name",
                     "description": "The name of the variable", "is_required": True, "name": "name",
                     "oasis": {"name": "name"}},
                    {"field_type": "json_value", "data_name": "value", "db_name": "value",
                     "description": "The value of the variable", "name": "value", "oasis": {"name": "value"}},
                ],
                "name": "variable",
            }],
            "field_descriptors": [
                {"field_type": "array", "base_type": "composite", "composite_type": "variable",
                 "data_name": "input_values", "db_name": "input_values",
                 "description": "The input variables to pass to the code. The inputs will be passed to run(...) as a dictionary.",
                 "name": "input_values", "oasis": {"name": "input_values"}},
                {"field_type": "composite", "composite_type": "devrev:schema", "data_name": "output_schema",
                 "db_name": "output_schema",
                 "description": "The schema of the output variables to return from the code. The outputs should be returned from run(...) as a dictionary.",
                 "name": "output_schema", "oasis": {"name": "output_schema"}},
                {"field_type": "text", "data_name": "code", "db_name": "code",
                 "default_value": "def run(inputs):\n    return {}",
                 "description": "Write your code here. Do not update the run function signature. The inputs will be passed to run(...) as a dictionary.",
                 "is_required": True, "name": "code", "oasis": {"name": "code"},
                 "ui": {"rich_text_metadata": {"code_editor_config": {"language": "python"}}}},
            ],
            "invalidate_on_field_update": ["output_schema", "input_values"],
            "type": "field_descriptor",
        },
        "type": "default",
    }


def _output_schema_field(name, field_type="text"):
    return {
        "description": "", "field_type": field_type, "is_filterable": False, "name": name,
        "ui": {"create_view": {}, "detail_view": {"is_hidden": True}, "display_name": name,
               "summary_view": {"is_hidden": True}},
    }


def _invoke_code_output_port(output_fields):
    descriptors = []
    for name, ft in output_fields:
        descriptors.append({
            "field_type": ft, "data_name": name, "db_name": name, "description": name,
            "name": name, "oasis": {"name": name},
        })
    return {"name": "output", "schema": {"field_descriptors": descriptors, "type": "field_descriptor"},
            "type": "default"}


def _composite_var(name, value_dict):
    """One input variable {name, value} for an invoke_code composite_value_list item."""
    return {"fields": [
        {"name": "value", "value": value_dict},
        {"name": "name", "value": {"type": "literal", "value": name}},
    ]}


def invoke_code_step(ref, name, description, code, input_vars, output_fields, position, next_step=None):
    """Build a fully-configured invoke_code step. `input_vars` is a list of (var_name, value_dict)."""
    items = [{"type": "composite_value_list", "value": [_composite_var(n, v) for (n, v) in input_vars]}]
    output_schema_fields = [_output_schema_field(n, ft) for (n, ft) in output_fields]
    step = {
        "name": name,
        "description": description,
        "reference_key": ref,
        "operation": {"namespace": "devrev", "slug": "invoke_code"},
        "input_ports": [_invoke_code_input_port()],
        "input_values": [{"port_name": "input", "fields": [
            {"name": "code", "value": {"type": "text_template", "value": code}},
            {"name": "input_values", "value": {"type": "list_value", "value": {"items": items}}},
            {"name": "output_schema", "value": {"type": "literal", "value": {"fields": output_schema_fields}}},
        ]}],
        "output_ports": [_invoke_code_output_port(output_fields), _error_output_port()],
        "ui_metadata": {"position": position},
    }
    if next_step:
        step["next_steps"] = [{"port_name": "output",
                               "next_step_reference_key": next_step,
                               "next_port_name": "input"}]
    return step


def jsonata(expr):
    return {"type": "jsonata_expression", "value": expr}


# ---------------------------------------------------------------------------
# Build the template.
# ---------------------------------------------------------------------------

def build_inner():
    steps = []

    # 1) Trigger: Ticket Created.  (fields_to_watch shape from the examples; the actual
    #    part + severity filter is applied in the UI after import.)
    steps.append({
        "name": "Ticket Created",
        "description": "Triggers when a ticket is created. In the UI, filter to your dedicated Part 3 test part AND severity == 'low' before publishing.",
        "reference_key": "ticket_created_1",
        "operation": {"namespace": "devrev", "slug": "ticket_created"},
        "input_values": [],
        "next_steps": [{"port_name": "output", "next_step_reference_key": "build_request_1", "next_port_name": "input"}],
        "ui_metadata": {"position": {"x": 0, "y": 0}},
    })

    # 2) build_request (Execute Code, with default-safe preflight).
    #    owned_by is mapped from the trigger owner objects to their .id via JSONata $map
    #    (grounded: JSONata is the expression language used in these examples).
    steps.append(invoke_code_step(
        ref="build_request_1",
        name="Build works.create request",
        description="Builds the works.create JSON body + external_ref. Default-safe preflight blocks live create unless the operator opts a single sandbox test ticket in.",
        code=BUILD_REQUEST_CODE,
        input_vars=[
            ("ticket_id", jsonata("$get('ticket_created_1', 'output').id")),
            ("title", jsonata("$get('ticket_created_1', 'output').title")),
            ("applies_to_part_id", jsonata("$get('ticket_created_1', 'output').applies_to_part.id")),
            ("owned_by_ids", jsonata("$map($get('ticket_created_1', 'output').owned_by, function($u){ $u.id })")),
            ("severity", jsonata("$get('ticket_created_1', 'output').severity")),
        ],
        output_fields=[("body", "text"), ("external_ref", "text"), ("endpoint", "text")],
        position={"x": 0, "y": 150},
        next_step="http_works_create_1",
    ))

    # 3) HTTP POST works.create.  (Shape verbatim from csat http_1: auth_type=Bearer literal,
    #    url/body=text_template, method=POST literal, Content-Type header, enable_retries=false.
    #    The Bearer auth token CONNECTION is selected in the UI after import - no token here.)
    steps.append({
        "name": "HTTP POST works.create",
        "description": "POST https://api.devrev.ai/works.create. Select an active sandbox Auth Token connection (Bearer) in the UI after import. No raw token is stored.",
        "reference_key": "http_works_create_1",
        "operation": {"namespace": "devrev", "slug": "http"},
        "input_ports": [{
            "name": "input",
            "schema": {
                "composite_schemas": [
                    {"description": "Key-value pair", "fields": [
                        {"field_type": "text", "data_name": "key", "db_name": "key", "description": "Key",
                         "is_required": True, "name": "key", "oasis": {"name": "key"}},
                        {"field_type": "text", "data_name": "value", "db_name": "value", "description": "Value",
                         "name": "value", "oasis": {"name": "value"}},
                    ], "name": "pair"},
                    {"description": "Transformation to apply to the HTTP response body", "fields": [
                        {"field_type": "text", "data_name": "jq", "db_name": "jq",
                         "description": "JQ query to apply to the HTTP response body.", "name": "jq",
                         "oasis": {"name": "jq"}},
                    ], "name": "transform"},
                ],
                "field_descriptors": [
                    {"field_type": "enum", "allowed_values": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                     "data_name": "method", "db_name": "method", "default_value": "GET",
                     "description": "Method of the HTTP request", "name": "method", "oasis": {"name": "method"}},
                    {"field_type": "array", "base_type": "composite", "composite_type": "pair",
                     "data_name": "query_params", "db_name": "query_params",
                     "description": "Query parameters of the HTTP request", "name": "query_params",
                     "oasis": {"name": "query_params"}},
                    {"field_type": "enum", "allowed_values": ["Bearer", "Basic", "None"], "data_name": "auth_type",
                     "db_name": "auth_type", "default_value": "None", "description": "Authentication type",
                     "name": "auth_type", "oasis": {"name": "auth_type"}},
                    {"field_type": "text", "data_name": "url", "db_name": "url",
                     "description": "URL of the HTTP request", "is_required": True, "name": "url",
                     "oasis": {"name": "url"}},
                    {"field_type": "array", "base_type": "composite", "composite_type": "pair",
                     "data_name": "headers", "db_name": "headers", "description": "Headers of the HTTP request",
                     "name": "headers", "oasis": {"name": "headers"}},
                    {"field_type": "text", "data_name": "body", "db_name": "body",
                     "description": "Body of the HTTP request", "name": "body", "oasis": {"name": "body"}},
                    {"field_type": "text", "data_name": "sample_response", "db_name": "sample_response",
                     "description": "Sample response of the HTTP response body", "is_required": False,
                     "name": "sample_response", "oasis": {"name": "sample_response"}},
                    {"field_type": "composite", "composite_type": "transform", "data_name": "transform",
                     "db_name": "transform", "description": "Transformation to apply to the HTTP response body",
                     "name": "transform", "oasis": {"name": "transform"}},
                    {"field_type": "bool", "data_name": "enable_retries", "db_name": "enable_retries",
                     "default_value": False, "description": "Enable retries on 5XX and 429 error codes",
                     "is_required": False, "name": "enable_retries", "oasis": {"name": "enable_retries"},
                     "ui": {"display_name": "Enable Retries"}},
                    {"field_type": "tokens", "data_name": "auth_header", "db_name": "auth_header",
                     "description": "Name of the authorization header.", "name": "auth_header",
                     "oasis": {"name": "auth_header"},
                     "ui": {"display_name": "Authorization Header", "placeholder": "Authorization"}},
                ],
                "invalidate_on_field_update": ["sample_response", "transform"],
                "type": "field_descriptor",
            },
            "type": "default",
        }],
        "input_values": [{"port_name": "input", "fields": [
            {"name": "method", "value": {"type": "literal", "value": "POST"}},
            {"name": "auth_type", "value": {"type": "literal", "value": "Bearer"}},
            {"name": "enable_retries", "value": {"type": "literal", "value": False}},
            {"name": "url", "value": {"type": "text_template", "value": WORKS_CREATE_URL}},
            {"name": "headers", "value": {"type": "list_value", "value": {"items": [
                {"type": "composite_value_list", "value": [{"fields": [
                    {"name": "key", "value": {"type": "literal", "value": "Content-Type"}},
                    {"name": "value", "value": {"type": "literal", "value": "application/json"}},
                ]}]},
            ]}}},
            {"name": "body", "value": {"type": "text_template",
                                       "value": "{% expr $get('build_request_1', 'output').body %}"}},
        ]}],
        "output_ports": [
            {"name": "output", "schema": {
                "composite_schemas": [{"description": "Key-value pair", "fields": [
                    {"field_type": "text", "data_name": "key", "db_name": "key", "description": "Key",
                     "is_required": True, "name": "key", "oasis": {"name": "key"}},
                    {"field_type": "text", "data_name": "value", "db_name": "value", "description": "Value",
                     "name": "value", "oasis": {"name": "value"}},
                ], "name": "pair"}],
                "field_descriptors": [
                    {"field_type": "int", "data_name": "status_code", "db_name": "status_code",
                     "description": "Status code of the HTTP request", "name": "status_code",
                     "oasis": {"name": "status_code"}},
                    {"field_type": "text", "data_name": "body", "db_name": "body",
                     "description": "Body of the HTTP response", "name": "body", "oasis": {"name": "body"}},
                    {"field_type": "array", "base_type": "composite", "composite_type": "pair",
                     "data_name": "headers", "db_name": "headers", "description": "Headers of the HTTP response",
                     "name": "headers", "oasis": {"name": "headers"}},
                    {"field_type": "text", "data_name": "content_type", "db_name": "content_type",
                     "description": "Content type of the HTTP response", "name": "content_type",
                     "oasis": {"name": "content_type"}},
                ],
                "type": "field_descriptor",
            }, "type": "default"},
            _error_output_port(),
        ],
        "next_steps": [{"port_name": "output", "next_step_reference_key": "validate_response_1", "next_port_name": "input"}],
        "ui_metadata": {"position": {"x": 0, "y": 300}},
    })

    # 4) validate_response (Execute Code). status_code + body bound from the HTTP output.
    steps.append(invoke_code_step(
        ref="validate_response_1",
        name="Validate works.create response",
        description="Raises on non-2xx or missing work.id/display_id so a bad HTTP finish is a FAILED run. VERIFY the real response field path in the sandbox and adjust if needed.",
        code=VALIDATE_RESPONSE_CODE,
        input_vars=[
            ("status_code", jsonata("$get('http_works_create_1', 'output').status_code")),
            ("response_body", jsonata("$get('http_works_create_1', 'output').body")),
        ],
        output_fields=[("work_id", "text"), ("display_id", "text")],
        position={"x": 0, "y": 450},
        next_step="reverse_severity_1",
    ))

    # 5) reverse_severity (Execute Code).
    steps.append(invoke_code_step(
        ref="reverse_severity_1",
        name="Reverse severity",
        description="Validates the lowercase severity enum then reverses it (low -> wol).",
        code=REVERSE_SEVERITY_CODE,
        input_vars=[("severity", jsonata("$get('ticket_created_1', 'output').severity"))],
        output_fields=[("reversed", "text"), ("original", "text")],
        position={"x": 0, "y": 600},
        next_step="comment_on_issue_1",
    ))

    # 6) add_comment on the CREATED ISSUE (object = validated work_id).
    steps.append({
        "name": "Comment on created issue",
        "description": "Internal comment on the created issue with the reversed severity.",
        "reference_key": "comment_on_issue_1",
        "operation": {"namespace": "devrev", "slug": "add_comment"},
        "input_ports": [_add_comment_input_port()],
        "input_values": [{"port_name": "input", "fields": [
            {"name": "object", "value": jsonata("$get('validate_response_1', 'output').work_id")},
            {"name": "visibility", "value": {"type": "literal", "value": "internal"}},
            {"name": "body", "value": {"type": "text_template",
                                       "value": "Reversed severity: {% expr $get('reverse_severity_1', 'output').reversed %} (from {% expr $get('reverse_severity_1', 'output').original %})."}},
        ]}],
        "next_steps": [{"port_name": "output", "next_step_reference_key": "comment_on_ticket_1", "next_port_name": "input"}],
        "ui_metadata": {"position": {"x": 0, "y": 750}},
    })

    # 7) add_comment on the TICKET (object = trigger ticket id).
    steps.append({
        "name": "Comment on ticket",
        "description": "Internal comment on the originating ticket referencing the new issue display_id.",
        "reference_key": "comment_on_ticket_1",
        "operation": {"namespace": "devrev", "slug": "add_comment"},
        "input_ports": [_add_comment_input_port()],
        "input_values": [{"port_name": "input", "fields": [
            {"name": "object", "value": jsonata("$get('ticket_created_1', 'output').id")},
            {"name": "visibility", "value": {"type": "literal", "value": "internal"}},
            {"name": "body", "value": {"type": "text_template",
                                       "value": "Linked issue {% expr $get('validate_response_1', 'output').display_id %} created for this ticket."}},
        ]}],
        "next_steps": [{"port_name": "output", "next_step_reference_key": "notify_policy_1", "next_port_name": "input"}],
        "ui_metadata": {"position": {"x": 0, "y": 900}},
    })

    # 8) notify_policy (Execute Code) -> plans the notification; should_notify defaults False.
    steps.append(invoke_code_step(
        ref="notify_policy_1",
        name="Notify policy (default-safe gate)",
        description="Plans the owner notification. should_notify is False by default unless the operator enables ALLOW_OWNER_NOTIFICATION and the owner matches the fixed test owner. No network call here.",
        code=NOTIFY_POLICY_CODE,
        input_vars=[
            ("work_id", jsonata("$get('validate_response_1', 'output').work_id")),
            ("display_id", jsonata("$get('validate_response_1', 'output').display_id")),
            ("reversed_severity", jsonata("$get('reverse_severity_1', 'output').reversed")),
            ("ticket_owner_id", jsonata("$get('ticket_created_1', 'output').owned_by[0].id")),
        ],
        output_fields=[("should_notify", "bool"), ("work_id", "text"), ("display_id", "text"),
                       ("issue_comment", "text"), ("notification", "text")],
        position={"x": 0, "y": 1050},
        next_step="notify_gate_1",
    ))

    # 9) if_else gate: should_notify == true -> send_notification; false -> safe end.
    #    (Condition group>group>rule shape verbatim from csat if_else_1.)
    steps.append({
        "name": "Notify gate",
        "description": "Native gate: only continue to send_notification when should_notify is true. The false branch ends safely (no notification).",
        "reference_key": "notify_gate_1",
        "operation": {"namespace": "devrev", "slug": "if_else"},
        "input_ports": [{
            "name": "input",
            "schema": {"field_descriptors": [
                {"field_type": "struct", "data_name": "condition", "db_name": "condition",
                 "description": "Condition to evaluate", "is_required": True, "name": "condition",
                 "oasis": {"name": "condition"}},
            ], "type": "field_descriptor"},
            "type": "default",
        }],
        "input_values": [{"port_name": "input", "fields": [
            {"name": "condition", "value": {"type": "literal", "value": {
                "type": "group", "logical_operator": "and", "negate": False, "conditions": [
                    {"type": "group", "logical_operator": "and", "negate": False, "conditions": [
                        {"type": "rule", "operator": "eq", "operands": [
                            {"type": "jsonata_expression", "value": "$get('notify_policy_1', 'output').should_notify"},
                            {"type": "literal", "value": True},
                        ]},
                    ]},
                ],
            }}},
        ]}],
        "output_ports": [
            {"name": "true", "type": "default"},
            {"name": "false", "type": "default"},
            _error_output_port(),
        ],
        "next_steps": [{"port_name": "true", "next_step_reference_key": "send_notification_1", "next_port_name": "input"}],
        "ui_metadata": {"position": {"x": 0, "y": 1200}},
    })

    # 10) send_notification (true branch).  (Shape verbatim from loop send_notification_1.)
    #     Receiver is bound dynamically to the trigger ticket owner. The gate above guarantees
    #     this only fires when should_notify is true (operator-owned test ticket).
    steps.append({
        "name": "Notify ticket owner",
        "description": "Notifies the ticket owner that the issue was created. Only reached when the notify gate is true.",
        "reference_key": "send_notification_1",
        "operation": {"namespace": "devrev", "slug": "send_notification"},
        "input_ports": [{
            "name": "input",
            "schema": {"field_descriptors": [
                {"field_type": "array", "base_type": "id", "data_name": "receivers", "db_name": "receivers",
                 "description": "The users or groups who will receive the notification", "id_type": ["devu", "group"],
                 "is_required": True, "name": "receivers", "oasis": {"name": "receivers"},
                 "ui": {"display_name": "Receivers"}},
                {"field_type": "rich_text", "data_name": "body", "db_name": "body",
                 "description": "The body of the notification", "is_required": True, "name": "body",
                 "oasis": {"name": "body"}, "ui": {"display_name": "Body"}},
                {"field_type": "rich_text", "data_name": "title", "db_name": "title",
                 "description": "The title of the notification", "is_required": True, "name": "title",
                 "oasis": {"name": "title"}, "ui": {"display_name": "Title"}},
                {"field_type": "id", "data_name": "content_template_id", "db_name": "content_template_id",
                 "description": "The content template for the notification",
                 "id_type": ["notification_content_template"], "is_required": False, "name": "content_template_id",
                 "oasis": {"name": "content_template_id"}, "ui": {"is_hidden": True}},
                {"field_type": "id", "data_name": "linked_object", "db_name": "linked_object",
                 "description": "The object which will open on clicking the notification",
                 "id_type": ["account", "capability", "enhancement", "feature", "incident", "issue", "linkable",
                             "opportunity", "product", "runnable", "ticket", "conversation"],
                 "is_required": False, "name": "linked_object", "oasis": {"name": "linked_object"},
                 "ui": {"display_name": "Linked Object"}},
            ], "type": "field_descriptor"},
            "type": "default",
        }],
        "input_values": [{"port_name": "input", "fields": [
            {"name": "receivers", "value": {"type": "list_value", "value": {"items": [
                jsonata("$get('ticket_created_1', 'output').owned_by[0].id"),
            ]}}},
            {"name": "title", "value": {"type": "text_template", "value": "Issue created for your ticket"}},
            {"name": "body", "value": {"type": "text_template",
                                       "value": "{% expr $get('notify_policy_1', 'output').notification %}"}},
            {"name": "linked_object", "value": jsonata("$get('validate_response_1', 'output').work_id")},
        ]}],
        "output_ports": [{"name": "output", "schema": {}, "type": "default"}, _error_output_port()],
        "ui_metadata": {"position": {"x": 0, "y": 1350}},
    })

    return {
        "description": ("DevRevU Part 3. Ticket Created (low) -> build works.create request (Execute Code, "
                        "default-safe preflight) -> HTTP POST works.create -> validate response (raises on "
                        "non-2xx) -> reverse severity -> comment on created issue -> comment on ticket -> "
                        "notify policy (default-safe) -> native if_else gate -> notify owner. The HTTP auth "
                        "connection and the safety guard constants are configured in the UI after import."),
        "serialization_version": {"major": 2, "minor": 0, "patch": 0},
        "steps": steps,
        "title": "DevRevU Part 3 - HTTP works.create + reverse severity",
    }


def _add_comment_input_port():
    return {
        "name": "input",
        "schema": {"field_descriptors": [
            {"field_type": "id", "data_name": "object", "db_name": "object", "description": "ID of the object",
             "id_type": ["account", "capability", "conversation", "enhancement", "feature", "incident", "issue",
                         "linkable", "opportunity", "product", "meeting", "revo", "revu", "runnable", "ticket",
                         "comment", "dm", "article"],
             "is_required": True, "name": "object", "oasis": {"name": "object"}},
            {"field_type": "text", "data_name": "body", "db_name": "body", "description": "Comment body",
             "is_required": True, "name": "body", "oasis": {"name": "body"}},
            {"field_type": "enum", "allowed_values": ["external", "internal", "private"], "data_name": "visibility",
             "db_name": "visibility", "default_value": "internal", "description": "Specifies the entry's visibility.",
             "is_required": False, "name": "visibility", "oasis": {"name": "visibility"}},
        ], "invalidate_on_field_update": ["visibility"], "type": "field_descriptor"},
        "type": "default",
    }


def build_envelope():
    inner = build_inner()
    return {"data": json.dumps(inner, separators=(",", ":"), ensure_ascii=False), "templateVersion": "2.0.0"}


def main(argv):
    if len(argv) < 2:
        print("usage: gen_template.py <out1.json> [<out2.json> ...]", file=sys.stderr)
        return 2
    envelope = build_envelope()
    text = json.dumps(envelope, indent=2, ensure_ascii=False) + "\n"
    for out in argv[1:]:
        d = os.path.dirname(os.path.abspath(out))
        if d and not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
