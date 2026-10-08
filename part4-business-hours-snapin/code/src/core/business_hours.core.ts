// TypeScript twin of business_hours.core.mjs. The .mjs version is the one actually
// unit-tested in this package (no toolchain assumptions). Keep the two in sync.
// This .ts version is what the snap-in build compiles.

export const MAX_TRANSITION_HOPS = 8;

// Definedness values that mean the schedule actually covers the instant (trustworthy). Any
// other value (undefined/unknown/missing-without-explicit-is_active) is a hard failure, not
// an "offline" guess.
export const DEFINED_DEFINEDNESS = new Set(["defined", "DEFINED"]);

export class ScheduleError extends Error {
  code: string;
  constructor(message: string, code = "schedule_error") {
    super(message);
    this.name = "ScheduleError";
    this.code = code;
  }
}

function assertDefined(ev: InstantEvaluation): void {
  const d = ev && ev.definedness;
  if (d === undefined || d === null) {
    if (typeof ev?.is_active === "boolean") return;
    throw new ScheduleError("schedule evaluation definedness is missing", "schedule_undefined");
  }
  if (!DEFINED_DEFINEDNESS.has(d)) {
    throw new ScheduleError(
      "schedule does not define this instant (definedness != defined)",
      "schedule_undefined"
    );
  }
}

export interface InstantEvaluation {
  at?: string;
  definedness?: string;
  is_active?: boolean;
  next_transition?: string | null;
}

export interface EvaluateResponse {
  instant_evaluations?: InstantEvaluation[];
}

export interface BusinessHoursResult {
  is_within_business_hours: boolean;
  next_open_time: string;
  evaluated_at: string;
}

export type EvaluateFn = (id: string, instantIso: string) => Promise<EvaluateResponse>;

export function parseTimestamp(ts: unknown): number {
  if (typeof ts !== "string" || ts.trim() === "") {
    throw new ScheduleError("timestamp is required (non-empty string)", "bad_timestamp");
  }
  const ms = Date.parse(ts);
  if (Number.isNaN(ms)) {
    throw new ScheduleError("timestamp is not a valid ISO-8601 datetime", "bad_timestamp");
  }
  return ms;
}

function pickEvaluation(resp: EvaluateResponse | undefined): InstantEvaluation {
  if (!resp || !Array.isArray(resp.instant_evaluations) || resp.instant_evaluations.length === 0) {
    throw new ScheduleError("org-schedules.evaluate returned no instant_evaluations", "schedule_unavailable");
  }
  return resp.instant_evaluations[0];
}

export async function evaluateBusinessHours(args: {
  orgScheduleId: string;
  timestamp: string;
  evaluate: EvaluateFn;
}): Promise<BusinessHoursResult> {
  const { orgScheduleId, timestamp, evaluate } = args;
  if (typeof orgScheduleId !== "string" || orgScheduleId.trim() === "") {
    throw new ScheduleError("org_schedule_id is required", "bad_input");
  }
  if (typeof evaluate !== "function") {
    throw new ScheduleError("evaluate function must be injected", "bad_input");
  }

  const atMs = parseTimestamp(timestamp);
  const atIso = new Date(atMs).toISOString();

  const first = pickEvaluation(await evaluate(orgScheduleId, atIso));
  assertDefined(first);
  if (first.is_active === true) {
    return { is_within_business_hours: true, next_open_time: "", evaluated_at: atIso };
  }

  let candidate = first.next_transition;
  for (let hop = 0; hop < MAX_TRANSITION_HOPS; hop++) {
    if (!candidate || typeof candidate !== "string") {
      return { is_within_business_hours: false, next_open_time: "", evaluated_at: atIso };
    }
    const candMs = Date.parse(candidate);
    if (Number.isNaN(candMs) || candMs <= atMs) {
      return { is_within_business_hours: false, next_open_time: "", evaluated_at: atIso };
    }
    const ev = pickEvaluation(await evaluate(orgScheduleId, new Date(candMs).toISOString()));
    assertDefined(ev);
    if (ev.is_active === true) {
      return { is_within_business_hours: false, next_open_time: new Date(candMs).toISOString(), evaluated_at: atIso };
    }
    candidate = ev.next_transition;
  }
  return { is_within_business_hours: false, next_open_time: "", evaluated_at: atIso };
}
