import { startupReducer, createInitialStartupSnapshot } from "../startup-machine";

describe("startupReducer", () => {
  it("starts idle", () => {
    expect(createInitialStartupSnapshot().status).toBe("idle");
  });

  it("RESET increments sequenceId and sets status running", () => {
    const initial = createInitialStartupSnapshot();
    const next = startupReducer(initial, { type: "RESET" });
    expect(next.sequenceId).toBe(initial.sequenceId + 1);
    expect(next.status).toBe("running");
  });

  it("records a phase start and completion with duration-computable timestamps", () => {
    let state = startupReducer(createInitialStartupSnapshot(), { type: "RESET" });
    state = startupReducer(state, { type: "PHASE_STARTED", phase: "initializing", at: "2026-01-01T00:00:00.000Z" });
    state = startupReducer(state, { type: "PHASE_COMPLETED", phase: "initializing", at: "2026-01-01T00:00:00.100Z", result: "success" });
    expect(state.phaseHistory).toHaveLength(1);
    expect(state.phaseHistory[0].result).toBe("success");
    expect(state.phaseHistory[0].completedAt).toBe("2026-01-01T00:00:00.100Z");
  });

  it("records a phase failure with error category and retry flag", () => {
    let state = startupReducer(createInitialStartupSnapshot(), { type: "RESET" });
    state = startupReducer(state, { type: "PHASE_STARTED", phase: "fetching-remote-config", at: "t0" });
    state = startupReducer(state, { type: "PHASE_FAILED", phase: "fetching-remote-config", at: "t1", category: "timeout", retryAllowed: true });
    expect(state.phaseHistory[0].result).toBe("error");
    expect(state.phaseHistory[0].errorCategory).toBe("timeout");
    expect(state.phaseHistory[0].retryAllowed).toBe(true);
  });

  it("does not corrupt an already-completed phase record when a later phase with the same name starts again (retry)", () => {
    let state = startupReducer(createInitialStartupSnapshot(), { type: "RESET" });
    state = startupReducer(state, { type: "PHASE_STARTED", phase: "fetching-remote-config", at: "t0" });
    state = startupReducer(state, { type: "PHASE_FAILED", phase: "fetching-remote-config", at: "t1", category: "timeout", retryAllowed: true });
    state = startupReducer(state, { type: "PHASE_STARTED", phase: "fetching-remote-config", at: "t2" });
    state = startupReducer(state, { type: "PHASE_COMPLETED", phase: "fetching-remote-config", at: "t3", result: "success" });
    expect(state.phaseHistory).toHaveLength(2);
    expect(state.phaseHistory[0].result).toBe("error");
    expect(state.phaseHistory[1].result).toBe("success");
  });

  it("READY sets status and readyAt", () => {
    const state = startupReducer(createInitialStartupSnapshot(), { type: "READY", at: "t" });
    expect(state.status).toBe("ready");
    expect(state.readyAt).toBe("t");
  });

  it("FAILED sets status and error details", () => {
    const state = startupReducer(createInitialStartupSnapshot(), { type: "FAILED", at: "t", category: "unknown", message: "boom", errorReferenceId: "ref_1" });
    expect(state.status).toBe("failed");
    expect(state.error?.errorReferenceId).toBe("ref_1");
  });

  it("is a pure function — same input always produces an equivalent output", () => {
    const state = createInitialStartupSnapshot();
    const a = startupReducer(state, { type: "READY", at: "t" });
    const b = startupReducer(state, { type: "READY", at: "t" });
    expect(a).toEqual(b);
  });
});
