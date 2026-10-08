// Dependency-free tests for the Business Hours core. Run: node business_hours.core.test.mjs
import assert from "node:assert/strict";
import {
  evaluateBusinessHours,
  parseTimestamp,
  ScheduleError,
  MAX_TRANSITION_HOPS,
} from "../src/core/business_hours.core.mjs";

let passed = 0;
let failed = 0;
async function test(name, fn) {
  try {
    await fn();
    passed++;
    console.log("  ok  -", name);
  } catch (e) {
    failed++;
    console.error("  FAIL-", name, "::", e.message);
  }
}

// Fake evaluate() that returns scripted responses keyed by instant ISO.
function fakeEvaluate(script) {
  return async (_id, instantIso) => {
    if (!(instantIso in script)) {
      throw new Error("unexpected instant queried: " + instantIso);
    }
    return { instant_evaluations: [script[instantIso]] };
  };
}

await test("within business hours -> true, no next time", async () => {
  const ts = "2026-10-08T10:00:00.000Z";
  const r = await evaluateBusinessHours({
    orgScheduleId: "sch_1",
    timestamp: ts,
    evaluate: fakeEvaluate({ [ts]: { at: ts, definedness: "defined", is_active: true, next_transition: null } }),
  });
  assert.equal(r.is_within_business_hours, true);
  assert.equal(r.next_open_time, "");
  assert.equal(r.evaluated_at, ts);
});

await test("outside hours with verified next opening", async () => {
  const ts = "2026-10-08T22:00:00.000Z";
  const next = "2026-10-09T01:00:00.000Z";
  const r = await evaluateBusinessHours({
    orgScheduleId: "sch_1",
    timestamp: ts,
    evaluate: fakeEvaluate({
      [ts]: { at: ts, definedness: "defined", is_active: false, next_transition: next },
      [next]: { at: next, definedness: "defined", is_active: true, next_transition: null },
    }),
  });
  assert.equal(r.is_within_business_hours, false);
  assert.equal(r.next_open_time, next);
});

await test("weekend (inactive) with no transition -> empty next time, not invented", async () => {
  const ts = "2026-10-10T10:00:00.000Z"; // Saturday
  const r = await evaluateBusinessHours({
    orgScheduleId: "sch_1",
    timestamp: ts,
    evaluate: fakeEvaluate({ [ts]: { at: ts, definedness: "defined", is_active: false, next_transition: null } }),
  });
  assert.equal(r.is_within_business_hours, false);
  assert.equal(r.next_open_time, "");
});

await test("holiday: first transition still closed, second verified open (bounded follow)", async () => {
  const ts = "2026-12-25T10:00:00.000Z"; // holiday, closed
  const t1 = "2026-12-26T01:00:00.000Z"; // still closed (weekend)
  const t2 = "2026-12-28T01:00:00.000Z"; // open
  const r = await evaluateBusinessHours({
    orgScheduleId: "sch_1",
    timestamp: ts,
    evaluate: fakeEvaluate({
      [ts]: { is_active: false, next_transition: t1 },
      [t1]: { is_active: false, next_transition: t2 },
      [t2]: { is_active: true, next_transition: null },
    }),
  });
  assert.equal(r.is_within_business_hours, false);
  assert.equal(r.next_open_time, t2);
});

await test("non-advancing transition (<= at) does not loop, returns empty", async () => {
  const ts = "2026-10-08T22:00:00.000Z";
  const past = "2026-10-08T09:00:00.000Z";
  const r = await evaluateBusinessHours({
    orgScheduleId: "sch_1",
    timestamp: ts,
    evaluate: fakeEvaluate({ [ts]: { is_active: false, next_transition: past } }),
  });
  assert.equal(r.next_open_time, "");
});

await test("invalid timestamp raises ScheduleError", async () => {
  await assert.rejects(
    () => evaluateBusinessHours({ orgScheduleId: "s", timestamp: "not-a-date", evaluate: async () => ({}) }),
    (e) => e instanceof ScheduleError && e.code === "bad_timestamp"
  );
});

await test("empty timestamp raises", async () => {
  await assert.rejects(() => evaluateBusinessHours({ orgScheduleId: "s", timestamp: "", evaluate: async () => ({}) }),
    (e) => e instanceof ScheduleError);
});

await test("missing org_schedule_id raises", async () => {
  await assert.rejects(() => evaluateBusinessHours({ orgScheduleId: "", timestamp: "2026-10-08T10:00:00Z", evaluate: async () => ({}) }),
    (e) => e instanceof ScheduleError && e.code === "bad_input");
});

await test("schedule unavailable (empty evaluations) is schedule_unavailable, not offline", async () => {
  const ts = "2026-10-08T10:00:00.000Z";
  await assert.rejects(
    () => evaluateBusinessHours({ orgScheduleId: "s", timestamp: ts, evaluate: async () => ({ instant_evaluations: [] }) }),
    (e) => e instanceof ScheduleError && e.code === "schedule_unavailable"
  );
});

await test("bounded loop never exceeds MAX_TRANSITION_HOPS (all closed, advancing)", async () => {
  const ts = "2026-10-08T00:00:00.000Z";
  let calls = 0;
  const evaluate = async (_id, instantIso) => {
    calls++;
    const nextMs = Date.parse(instantIso) + 3600_000;
    return { instant_evaluations: [{ is_active: false, next_transition: new Date(nextMs).toISOString() }] };
  };
  const r = await evaluateBusinessHours({ orgScheduleId: "s", timestamp: ts, evaluate });
  assert.equal(r.is_within_business_hours, false);
  assert.equal(r.next_open_time, "");
  // 1 initial + up to MAX_TRANSITION_HOPS follow-ups
  assert.ok(calls <= 1 + MAX_TRANSITION_HOPS, "calls bounded, got " + calls);
});

await test("parseTimestamp returns epoch millis", () => {
  assert.equal(parseTimestamp("1970-01-01T00:00:00.000Z"), 0);
});

await test("undefined definedness fails (does NOT guess offline)", async () => {
  const ts = "2027-01-01T10:00:00.000Z";
  await assert.rejects(
    () => evaluateBusinessHours({
      orgScheduleId: "s",
      timestamp: ts,
      evaluate: fakeEvaluate({ [ts]: { at: ts, definedness: "undefined", is_active: false, next_transition: null } }),
    }),
    (e) => e instanceof ScheduleError && e.code === "schedule_undefined"
  );
});

await test("unknown definedness fails", async () => {
  const ts = "2027-01-01T10:00:00.000Z";
  await assert.rejects(
    () => evaluateBusinessHours({
      orgScheduleId: "s",
      timestamp: ts,
      evaluate: fakeEvaluate({ [ts]: { at: ts, definedness: "unknown", is_active: true, next_transition: null } }),
    }),
    (e) => e instanceof ScheduleError && e.code === "schedule_undefined"
  );
});

await test("defined is_active true -> within hours", async () => {
  const ts = "2026-10-08T10:00:00.000Z";
  const r = await evaluateBusinessHours({
    orgScheduleId: "s",
    timestamp: ts,
    evaluate: fakeEvaluate({ [ts]: { definedness: "defined", is_active: true, next_transition: null } }),
  });
  assert.equal(r.is_within_business_hours, true);
});

await test("evaluate() timeout/abort propagates (no token/no fabricated time)", async () => {
  const ts = "2026-10-08T10:00:00.000Z";
  const timingOut = async () => {
    const err = new Error("The operation was aborted");
    err.name = "AbortError";
    throw err; // simulates the adapter's AbortController firing
  };
  await assert.rejects(
    () => evaluateBusinessHours({ orgScheduleId: "s", timestamp: ts, evaluate: timingOut }),
    (e) => e.name === "AbortError"
  );
});

await test("DST spring-forward boundary: next opening after skipped hour (mocked schedule)", async () => {
  // US DST 2026-03-08: 02:00 -> 03:00 local. We mock the server schedule's transitions so the
  // core follows them verbatim rather than computing wall-clock offsets itself.
  const ts = "2026-03-08T06:30:00.000Z"; // closed (early Sunday UTC)
  const open = "2026-03-09T13:00:00.000Z"; // next business opening per server (post-DST)
  const r = await evaluateBusinessHours({
    orgScheduleId: "s",
    timestamp: ts,
    evaluate: fakeEvaluate({
      [ts]: { definedness: "defined", is_active: false, next_transition: open },
      [open]: { definedness: "defined", is_active: true, next_transition: null },
    }),
  });
  assert.equal(r.is_within_business_hours, false);
  assert.equal(r.next_open_time, open);
});

await test("DST fall-back boundary: active instant returns within hours with empty next (mocked)", async () => {
  const ts = "2026-11-01T15:00:00.000Z"; // within hours per server across the repeated hour
  const r = await evaluateBusinessHours({
    orgScheduleId: "s",
    timestamp: ts,
    evaluate: fakeEvaluate({ [ts]: { definedness: "defined", is_active: true, next_transition: null } }),
  });
  assert.equal(r.is_within_business_hours, true);
  assert.equal(r.next_open_time, "");
});

await test("active with a next_transition (closing time) still returns empty next_open_time", async () => {
  // When active, next_transition is the CLOSING time, not an opening. We must NOT surface it.
  const ts = "2026-10-08T10:00:00.000Z";
  const r = await evaluateBusinessHours({
    orgScheduleId: "s",
    timestamp: ts,
    evaluate: fakeEvaluate({ [ts]: { definedness: "defined", is_active: true, next_transition: "2026-10-08T18:00:00.000Z" } }),
  });
  assert.equal(r.is_within_business_hours, true);
  assert.equal(r.next_open_time, "");
});

console.log(`\nBusiness Hours core: ${passed} passed, ${failed} failed`);
if (failed > 0) process.exit(1);
