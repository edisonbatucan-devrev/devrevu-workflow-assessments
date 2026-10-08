// Part 4 - Business Hours Validator custom operation (3P node) - SDK ADAPTER.
//
// IMPORTANT: This adapter was NOT compiled or runtime-validated in this package (no snap-in
// toolchain / SDK installed here). The business logic it calls IS tested via
// ../../core/business_hours.core.ts (and the .mjs twin). Treat SDK import paths and the
// event field accessors below as CANDIDATES to confirm with `devrev snap_in` + the current
// @devrev/typescript-sdk docs before deploy. Points flagged "VERIFY" need checking against
// the runtime adapter.

import {
  OperationBase,
  OperationContext,
  ExecuteOperationInput,
  OperationOutput,
  FunctionInput,
  Error as SdkError,
  Error_Type,
} from "@devrev/typescript-sdk/dist/snap-ins";

import { evaluateBusinessHours, ScheduleError } from "../../core/business_hours.core";

// Bounded HTTP timeout; never log credentials or full responses.
const EVALUATE_TIMEOUT_MS = 8000;

interface Inputs {
  org_schedule_id: string;
  timestamp: string;
}

// Minimal POST to org-schedules.evaluate. Credentials come from the service account token
// secret; they are never logged.
async function callEvaluate(
  endpoint: string,
  token: string,
  id: string,
  instantIso: string
): Promise<unknown> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), EVALUATE_TIMEOUT_MS);
  try {
    const res = await fetch(`${endpoint}/org-schedules.evaluate`, {
      method: "POST",
      headers: {
        Authorization: token, // service account token; do NOT log
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ id, instants: [instantIso] }),
      signal: controller.signal,
    });
    if (!res.ok) {
      // Schedule/API failure. Bounded, non-leaking message.
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
  // VERIFY: the exact OperationBase method name/signature against the SDK version used.
  async run(context: OperationContext, input: ExecuteOperationInput): Promise<OperationOutput> {
    try {
      // VERIFY: input.data field path for operation inputs in the runtime adapter.
      const data = (input as unknown as { data?: Inputs }).data ?? ({} as Inputs);
      const orgScheduleId = data.org_schedule_id;
      const timestamp = data.timestamp;

      // VERIFY: these accessors against the runtime event/context adapter.
      const endpoint =
        (context as unknown as { devrev_endpoint?: string }).devrev_endpoint ||
        process.env.DEVREV_ENDPOINT ||
        "https://api.devrev.ai";
      const token =
        (context as unknown as { secrets?: { service_account_token?: string } }).secrets
          ?.service_account_token || "";

      if (!token) {
        return OperationOutput.fromJSON({
          error: { type: Error_Type.InvalidRequest, message: "Missing service account token secret." },
        } as unknown as object);
      }

      const result = await evaluateBusinessHours({
        orgScheduleId,
        timestamp,
        evaluate: (id, instantIso) => callEvaluate(endpoint, token, id, instantIso) as Promise<any>,
      });

      // Configure outputs explicitly.
      return OperationOutput.fromJSON({
        output: {
          values: [
            {
              is_within_business_hours: result.is_within_business_hours,
              next_open_time: result.next_open_time, // empty string if active / unknown
              evaluated_at: result.evaluated_at,
            },
          ],
        },
      } as unknown as object);
    } catch (e) {
      const code =
        e instanceof ScheduleError ? e.code : "internal_error";
      const message =
        e instanceof Error ? e.message : "Unknown error evaluating business hours.";
      // Structured error. No credential/body leakage.
      return OperationOutput.fromJSON({
        error: {
          type: Error_Type.InvalidRequest,
          message: `[${code}] ${message}`,
        },
      } as unknown as object);
    }
  }
}

// VERIFY: how your snap-in function entrypoint registers/dispatches operations.
export async function run(events: FunctionInput[]): Promise<OperationOutput[]> {
  const op = new BusinessHoursValidator();
  const outputs: OperationOutput[] = [];
  for (const event of events) {
    // VERIFY: event.payload.data vs event.input_data in the runtime adapter.
    const context = {
      devrev_endpoint: event?.execution_metadata?.devrev_endpoint,
      secrets: { service_account_token: event?.context?.secrets?.service_account_token },
    } as unknown as OperationContext;
    const input = { data: (event as unknown as { payload?: { data?: unknown } }).payload?.data } as unknown as ExecuteOperationInput;
    outputs.push(await op.run(context, input));
  }
  return outputs;
}

export default run;

// Silence unused-import lint for SdkError until wired; kept for parity with SDK examples.
void (SdkError as unknown);
