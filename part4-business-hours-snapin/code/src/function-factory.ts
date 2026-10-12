// Standard snap-in function factory (platform bootstrap entrypoint).
//
// Mirrors the official devrev/snap-in-examples 14-operations src/function-factory.ts and the
// devrev/devrev-snaps-typescript-template: the platform runtime loads the compiled package
// entrypoint (package.json "main" -> dist/index.js, which re-exports this module) and resolves
// the function to run by its MANIFEST FUNCTION NAME, looked up as a key in `functionFactory`.
// The value is that function's handler (default export), invoked as run(events).
//
// The key here MUST equal manifest `functions[].name` (business_hours_validator). The previous
// local runner called the handler module directly; this registration is what the platform
// bootstrap needs so the function is discoverable by name at deploy/runtime.
//
// ESM note: this package is `type: module` with Bundler resolution; the handler is imported with
// its compiled relative `.js` path (same convention as the rest of src/).

import business_hours_validator from "./functions/business_hours_validator/index.js";

export const functionFactory = {
  // Add your functions here, keyed by the manifest function name.
  business_hours_validator,
} as const;

export type FunctionFactoryType = keyof typeof functionFactory;
