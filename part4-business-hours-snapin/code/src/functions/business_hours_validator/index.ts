// Part 4 - Business Hours Validator custom operation (3P node) - SDK ADAPTER.
//
// This adapter is wired against the ACTUAL installed @devrev/typescript-sdk (v1.1.79) snap-in
// types and mirrors the official operations example
// (devrev/snap-in-examples 14-operations: operation_handler + operations factory). The
// business logic it calls is tested via ../../core/business_hours.core.ts (and the .mjs twin),
// and the SDK input/output wiring here is covered by index.test.mjs with a fake injected
// transport (no live API calls).
//
// The operation class extends OperationBase, whose constructor REQUIRES the FunctionInput
// event (constructor(event: FunctionInput)). The context (devrev_endpoint + secrets) comes
// from the SDK's GetContext(); do NOT read process.env or any user-controlled host.

import {
  Error as SdkError,
  Error_Type,
  ExecuteOperationInput,
  FunctionInput,
  OperationBase,
  OperationContext,
  OperationMap,
  OperationOutput,
  OutputValue,
} from "@devrev/typescript-sdk/dist/snap-ins/index.js";

import { evaluateBusinessHours, ScheduleError } from "../../core/business_hours.core.js";

// Bounded HTTP timeout; never log credentials or full responses.
export const EVALUATE_TIMEOUT_MS = 8000;

interface Inputs {
  org_schedule_id: string;
  timestamp: string;
}

// Minimal POST to org-schedules.evaluate. The access token comes from the operation context
// secrets; it is never logged. The endpoint is the SDK-provided DevRev endpoint only.
async function callEvaluate(
  endpoint: string,
  token: string,
  id: string,
  instantIso: string
): Promise<unknown> {
  const base = endpoint.replace(/\/+$/, "");
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), EVALUATE_TIMEOUT_MS);
  try {
    const res = await fetch(`${base}/org-schedules.evaluate`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`, // access token; do NOT log
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ id, instants: [instantIso] }),
      signal: controller.signal,
    });
    if (!res.ok) {
      // Schedule/API failure. Bounded, non-leaking message (status only, no body).
      throw new ScheduleError(
        `org-schedules.evaluate returned HTTP ${res.status}`,
        "schedule_unavailable"
      );
    }
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}

export class BusinessHoursValidator extends OperationBase {
  constructor(e: FunctionInput) {
    super(e);
  }

  async run(
    context: OperationContext,
    input: ExecuteOperationInput,
    _resources: Record<string, any>
  ): Promise<OperationOutput> {
    try {
      const data = (input.data ?? {}) as Inputs;
      const orgScheduleId = data.org_schedule_id;
      const timestamp = data.timestamp;

      // Endpoint and credentials come ONLY from the SDK operation context (populated by the
      // platform via OperationBase.GetContext). No env/user-controlled host fallback.
      const endpoint = context.devrev_endpoint;
      const token = context.secrets?.access_token || "";

      if (!endpoint) {
        return makeError(Error_Type.InvalidRequest, "Missing DevRev endpoint in context.");
      }
      if (!token) {
        return makeError(Error_Type.InvalidRequest, "Missing access token in context secrets.");
      }

      const result = await evaluateBusinessHours({
        orgScheduleId,
        timestamp,
        evaluate: (id, instantIso) =>
          callEvaluate(endpoint, token, id, instantIso) as Promise<any>,
      });

      const output: OutputValue = {
        values: [
          {
            is_within_business_hours: result.is_within_business_hours,
            next_open_time: result.next_open_time, // empty string if active / unknown
            evaluated_at: result.evaluated_at,
          },
        ],
      };
      return OperationOutput.fromJSON({ output });
    } catch (e) {
      const code = e instanceof ScheduleError ? e.code : "internal_error";
      const message =
        e instanceof Error ? e.message : "Unknown error evaluating business hours.";
      // Structured error. No credential/body leakage.
      return makeError(Error_Type.InvalidRequest, `[${code}] ${message}`);
    }
  }
}

function makeError(type: Error_Type, message: string): OperationOutput {
  const err: SdkError = { message, type };
  return OperationOutput.fromJSON({ error: err });
}

// Operation slug -> operation class, keyed by the slug declared in the manifest.
export const operationMap: OperationMap = {
  "business-hours-validator": BusinessHoursValidator,
};

// Snap-in function entrypoint. Mirrors the official operation_handler: resolve the operation
// by slug from the ExecuteOperationInput payload, instantiate with the event, build the
// context via the SDK's GetContext(), then run with (context, payload, resources).
export const run = async (events: FunctionInput[]): Promise<OperationOutput> => {
  const event = events[0];
  const payload = event.payload as ExecuteOperationInput;
  const slug = payload.metadata?.slug;
  if (!slug || !operationMap[slug]) {
    return makeError(Error_Type.InvalidRequest, `Unknown operation slug: ${String(slug)}`);
  }
  const operation = new operationMap[slug](event);
  const context = operation.GetContext();
  const resources = event.input_data?.resources || {};
  return await operation.run(context, payload, resources);
};

export default run;
