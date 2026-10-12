// Adapter tests for the Business Hours Validator SDK wrapper.
//
// These drive the REAL compiled operation (dist/functions/business_hours_validator/index.js)
// through the REAL @devrev/typescript-sdk OperationBase / OperationOutput wrapper, with a
// FAKE injected transport (global fetch stub) so NO live API call is made. Run after build:
//   npm run build && node test/business_hours.adapter.test.mjs
//
// What this proves beyond the core tests: the SDK operation input (ExecuteOperationInput.data)
// is read correctly, the context (devrev_endpoint + secrets.access_token) is consumed from
// OperationBase.GetContext(), the request to org-schedules.evaluate has the right shape
// ({id, instants:[iso]}, Bearer auth, HTTPS DevRev host), and the OperationOutput shape
// (output.values[0] / structured error) is what the runtime expects.

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { run, BusinessHoursValidator } from "../dist/functions/business_hours_validator/index.js";
// Standard platform bootstrap entrypoint: dist/index.js re-exports the function factory, which
// registers the manifest function by name. These are what the platform resolves at deploy/runtime.
import { functionFactory } from "../dist/index.js";

let passed = 0;
let failed = 0;
async function test(name, fn) {
  const savedFetch = globalThis.fetch;
  try {
    await fn();
    passed++;
    console.log("  ok  -", name);
  } catch (e) {
    failed++;
    console.error("  FAIL-", name, "::", e.message);
  } finally {
    globalThis.fetch = savedFetch;
  }
}

const TOKEN = "svc-token-SECRET-should-never-leak";
const ENDPOINT = "https://api.devrev.ai";

// Build a FunctionInput event the way the platform delivers an ExecuteOperationInput payload.
function makeEvent({ org_schedule_id, timestamp, token = TOKEN, endpoint = ENDPOINT }) {
  return {
    payload: {
      metadata: { namespace: "", slug: "business-hours-validator", type: 0 },
      input_port_name: "default",
      data: { org_schedule_id, timestamp },
      operation_method: "",
      input_configuration: {},
      state: {},
      block_callback: undefined,
    },
    context: {
      dev_oid: "DEV-0",
      source_id: "src",
      snap_in_id: "si",
      snap_in_version_id: "siv",
      service_account_id: "sa",
      secrets: { access_token: token },
    },
    execution_metadata: {
      request_id: "req-1",
      function_name: "business_hours_validator",
      event_type: "operation",
      devrev_endpoint: endpoint,
    },
    input_data: { global_values: {}, event_sources: {}, resources: {} },
  };
}

// A fake fetch that records the request and returns scripted org-schedules.evaluate responses
// keyed by the instant queried. `requests` is populated so tests can assert request shape.
function installFakeFetch(script, requests) {
  globalThis.fetch = async (url, init) => {
    const body = JSON.parse(init.body);
    requests.push({ url, headers: init.headers, body });
    const instant = body.instants[0];
    const ev = script[instant];
    if (ev === undefined) throw new Error("unexpected instant queried: " + instant);
    if (ev.__http) {
      return { ok: false, status: ev.__http, json: async () => ({}) };
    }
    return { ok: true, status: 200, json: async () => ({ instant_evaluations: [ev] }) };
  };
}

// Pull the single default-port output values object out of an OperationOutput.
function firstValues(output) {
  return output.output.values[0];
}

await test("within hours -> output.values[0].is_within_business_hours true, empty next", async () => {
  const ts = "2026-10-08T10:00:00.000Z";
  const requests = [];
  installFakeFetch({ [ts]: { definedness: "defined", is_active: true, next_transition: null } }, requests);

  const out = await run([makeEvent({ org_schedule_id: "sch_1", timestamp: ts })]);
  const v = firstValues(out);
  assert.equal(v.is_within_business_hours, true);
  assert.equal(v.next_open_time, "");
  assert.equal(v.evaluated_at, ts);
  assert.equal(out.error, undefined);

  // Request shape + security assertions.
  assert.equal(requests.length, 1);
  assert.ok(requests[0].url.startsWith("https://api.devrev.ai/"), "HTTPS DevRev host only");
  assert.ok(requests[0].url.endsWith("/org-schedules.evaluate"));
  assert.equal(requests[0].headers.Authorization, `Bearer ${TOKEN}`);
  assert.equal(requests[0].body.id, "sch_1");
  assert.deepEqual(requests[0].body.instants, [ts]);
});

await test("outside hours -> follows transition, verified next_open_time", async () => {
  const ts = "2026-10-08T22:00:00.000Z";
  const next = "2026-10-09T01:00:00.000Z";
  const requests = [];
  installFakeFetch({
    [ts]: { definedness: "defined", is_active: false, next_transition: next },
    [next]: { definedness: "defined", is_active: true, next_transition: null },
  }, requests);

  const out = await run([makeEvent({ org_schedule_id: "sch_1", timestamp: ts })]);
  const v = firstValues(out);
  assert.equal(v.is_within_business_hours, false);
  assert.equal(v.next_open_time, next);
  assert.equal(requests.length, 2);
});

await test("missing access token -> structured error, no network call", async () => {
  const ts = "2026-10-08T10:00:00.000Z";
  const requests = [];
  installFakeFetch({}, requests);
  const out = await run([makeEvent({ org_schedule_id: "sch_1", timestamp: ts, token: "" })]);
  assert.ok(out.error, "error must be set");
  assert.equal(out.error.type, 1); // Error_Type.InvalidRequest
  assert.equal(requests.length, 0, "no network call when token is missing");
});

await test("schedule HTTP failure -> schedule_unavailable error, status only (no body leak)", async () => {
  const ts = "2026-10-08T10:00:00.000Z";
  const requests = [];
  installFakeFetch({ [ts]: { __http: 503 } }, requests);
  const out = await run([makeEvent({ org_schedule_id: "sch_1", timestamp: ts })]);
  assert.ok(out.error);
  assert.match(out.error.message, /schedule_unavailable/);
  assert.match(out.error.message, /HTTP 503/);
});

await test("invalid timestamp -> bad_timestamp error, no credential in message", async () => {
  const requests = [];
  installFakeFetch({}, requests);
  const out = await run([makeEvent({ org_schedule_id: "sch_1", timestamp: "not-a-date" })]);
  assert.ok(out.error);
  assert.match(out.error.message, /bad_timestamp/);
  assert.ok(!out.error.message.includes(TOKEN), "token must never appear in error message");
  assert.equal(requests.length, 0);
});

await test("unknown operation slug -> structured error", async () => {
  const ev = makeEvent({ org_schedule_id: "s", timestamp: "2026-10-08T10:00:00.000Z" });
  ev.payload.metadata.slug = "not-registered";
  const out = await run([ev]);
  assert.ok(out.error);
  assert.match(out.error.message, /Unknown operation slug/);
});

await test("operation class requires a FunctionInput event (OperationBase contract)", async () => {
  // Guards against regressing to `new BusinessHoursValidator()` with no args.
  assert.equal(BusinessHoursValidator.length, 1, "constructor arity must be 1 (the event)");
});

await test("manifest keeps operation labels separate from field UI labels", async () => {
  const manifest = readFileSync(new URL("../manifest.example.yaml", import.meta.url), "utf8");
  assert.match(manifest, /^    display_name: Business Hour Validator$/m);
  assert.doesNotMatch(manifest, /^    ui:\s*$/m, "no extra operation-level UI block");
  assert.match(manifest, /^            display_name: Org schedule ID$/m);
  assert.match(manifest, /^            display_name: Is within business hours$/m);
  // This guards the field layout; sandbox validation is still required.
});

// --- Standard platform entrypoint (function-factory / dist/index.js) regression tests ---
// These prove the function is discoverable by its MANIFEST FUNCTION NAME via the compiled
// standard entry (dist/index.js -> functionFactory), not only via the direct handler module.
// A missing factory registration is exactly the packaging gap the platform bootstrap hits.

await test("entrypoint exposes exactly the manifest function name key", async () => {
  assert.ok(functionFactory, "functionFactory must be exported from dist/index.js");
  assert.deepEqual(Object.keys(functionFactory), ["business_hours_validator"]);
  assert.equal(typeof functionFactory.business_hours_validator, "function");
  // The factory value is the same handler the direct module exports.
  assert.equal(functionFactory.business_hours_validator, run);
});

await test("entrypoint dispatch by function name -> success through fake fetch (no live API)", async () => {
  const ts = "2026-10-08T10:00:00.000Z";
  const requests = [];
  installFakeFetch({ [ts]: { definedness: "defined", is_active: true, next_transition: null } }, requests);

  // Resolve the handler exactly as the platform would: by manifest function name.
  const handler = functionFactory["business_hours_validator"];
  const out = await handler([makeEvent({ org_schedule_id: "sch_1", timestamp: ts })]);
  const v = firstValues(out);
  assert.equal(v.is_within_business_hours, true);
  assert.equal(v.next_open_time, "");
  assert.equal(out.error, undefined);
  assert.equal(requests.length, 1);
  assert.ok(requests[0].url.startsWith("https://api.devrev.ai/"), "HTTPS DevRev host only");
});

await test("unknown function name is not registered -> fail-closed (no handler, no network)", async () => {
  const requests = [];
  installFakeFetch({}, requests);
  const handler = functionFactory["not_a_real_function"];
  assert.equal(handler, undefined, "unregistered function names must not resolve to a handler");
  assert.equal(requests.length, 0, "no network call for an unknown function name");
});

await test("entrypoint handler fails closed on a malformed event (no network, structured error)", async () => {
  const requests = [];
  installFakeFetch({}, requests);
  const handler = functionFactory["business_hours_validator"];
  // Malformed: payload has no operation metadata/slug at all.
  const malformed = { payload: {}, context: {}, execution_metadata: {}, input_data: {} };
  const out = await handler([malformed]);
  assert.ok(out.error, "malformed event must produce a structured error, not throw");
  assert.match(out.error.message, /Unknown operation slug/);
  assert.equal(requests.length, 0, "no network call on a malformed event");
});

console.log(`\nBusiness Hours adapter: ${passed} passed, ${failed} failed`);
if (failed > 0) process.exit(1);
