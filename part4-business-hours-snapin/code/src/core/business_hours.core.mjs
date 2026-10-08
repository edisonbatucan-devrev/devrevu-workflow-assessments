// Part 4 - Business Hours Validator CORE logic (dependency-free, testable).
//
// This module contains the pure business logic for the "Business Hour Validator" custom
// operation. It has NO DevRev SDK import and NO direct network/credential handling, so it
// can be unit-tested with plain Node. The SDK adapter (business_hours_validator/index.ts)
// wires this core to event.payload / secrets / the org-schedules.evaluate HTTP call.
//
// org-schedules.evaluate contract (from the exercise brief):
//   request:  { id, instants: [timestamp] }
//   response: { instant_evaluations: [ { at, definedness, is_active, next_transition } ] }
// When inactive, next_transition is a CANDIDATE next opening. We FOLLOW transitions and
// re-evaluate to verify the schedule is actually active there, with a BOUNDED loop. We
// never invent a next time: if we cannot verify an open instant within the bound, we
// return an empty next_open_time rather than a fabricated one.

export const MAX_TRANSITION_HOPS = 8; // bounded loop guard

// Definedness values we treat as "the schedule actually covers this instant and the result
// is trustworthy". Any other value (e.g. "undefined", "unknown", missing) means the schedule
// does not define this instant, and we must FAIL rather than guess "offline".
export const DEFINED_DEFINEDNESS = new Set(["defined", "DEFINED"]);

export class ScheduleError extends Error {
  constructor(message, code) {
    super(message);
    this.name = "ScheduleError";
    this.code = code || "schedule_error";
  }
}

// A single evaluation is trustworthy only when its definedness says the schedule covers the
// instant. We tolerate a MISSING definedness ONLY when is_active is an explicit boolean,
// because some responses omit definedness for clearly-covered instants; anything explicitly
// undefined/unknown is a hard failure (do NOT assume offline).
function assertDefined(ev) {
  const d = ev && ev.definedness;
  if (d === undefined || d === null) {
    if (typeof ev?.is_active === "boolean") return; // tolerate omission with explicit is_active
    throw new ScheduleError("schedule evaluation definedness is missing", "schedule_undefined");
  }
  if (!DEFINED_DEFINEDNESS.has(d)) {
    throw new ScheduleError(
      "schedule does not define this instant (definedness != defined)",
      "schedule_undefined"
    );
  }
}

// Validate an ISO-8601-ish timestamp string and return epoch millis.
// Rejects empty/garbage. This is the "offset timestamp validation" the brief calls for.
export function parseTimestamp(ts) {
  if (typeof ts !== "string" || ts.trim() === "") {
    throw new ScheduleError("timestamp is required (non-empty string)", "bad_timestamp");
  }
  const ms = Date.parse(ts);
  if (Number.isNaN(ms)) {
    throw new ScheduleError("timestamp is not a valid ISO-8601 datetime", "bad_timestamp");
  }
  return ms;
}

// Read a single evaluation from a response for a given instant.
function pickEvaluation(resp) {
  if (!resp || !Array.isArray(resp.instant_evaluations) || resp.instant_evaluations.length === 0) {
    // Schedule unavailable / expired / empty response is a SCHEDULE error, NOT "offline".
    throw new ScheduleError("org-schedules.evaluate returned no instant_evaluations", "schedule_unavailable");
  }
  return resp.instant_evaluations[0];
}

/**
 * Core evaluation.
 * @param {Object} args
 * @param {string} args.orgScheduleId
 * @param {string} args.timestamp - ISO-8601 string to check.
 * @param {(id:string, instantIso:string)=>Promise<Object>} args.evaluate - injected HTTP caller.
 *        Must POST org-schedules.evaluate {id, instants:[instant]} and return the parsed JSON.
 * @returns {Promise<{is_within_business_hours:boolean, next_open_time:string, evaluated_at:string}>}
 */
export async function evaluateBusinessHours({ orgScheduleId, timestamp, evaluate }) {
  if (typeof orgScheduleId !== "string" || orgScheduleId.trim() === "") {
    throw new ScheduleError("org_schedule_id is required", "bad_input");
  }
  if (typeof evaluate !== "function") {
    throw new ScheduleError("evaluate function must be injected", "bad_input");
  }

  // Validate + normalize the requested instant.
  const atMs = parseTimestamp(timestamp);
  const atIso = new Date(atMs).toISOString();

  const first = pickEvaluation(await evaluate(orgScheduleId, atIso));
  assertDefined(first);

  if (first.is_active === true) {
    return { is_within_business_hours: true, next_open_time: "", evaluated_at: atIso };
  }

  // Inactive: follow next_transition candidates and VERIFY an active instant. Bounded.
  let candidate = first.next_transition;
  for (let hop = 0; hop < MAX_TRANSITION_HOPS; hop++) {
    if (!candidate || typeof candidate !== "string") {
      // No further transition known -> do NOT invent a time.
      return { is_within_business_hours: false, next_open_time: "", evaluated_at: atIso };
    }
    // Guard against non-advancing / past transitions.
    const candMs = Date.parse(candidate);
    if (Number.isNaN(candMs) || candMs <= atMs) {
      return { is_within_business_hours: false, next_open_time: "", evaluated_at: atIso };
    }
    const ev = pickEvaluation(await evaluate(orgScheduleId, new Date(candMs).toISOString()));
    assertDefined(ev);
    if (ev.is_active === true) {
      return {
        is_within_business_hours: false,
        next_open_time: new Date(candMs).toISOString(),
        evaluated_at: atIso,
      };
    }
    candidate = ev.next_transition;
  }
  // Exhausted bound without verifying an opening: return empty rather than a guess.
  return { is_within_business_hours: false, next_open_time: "", evaluated_at: atIso };
}
