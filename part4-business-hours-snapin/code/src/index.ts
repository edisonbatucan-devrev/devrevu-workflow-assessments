// Compiled package entrypoint (package.json "main" -> dist/index.js).
//
// Mirrors the official devrev/snap-in-examples 14-operations src/index.ts: it simply re-exports
// the function factory so the platform runtime can bootstrap and resolve snap-in functions by
// their manifest name. No runtime side effects.

export * from "./function-factory.js";
