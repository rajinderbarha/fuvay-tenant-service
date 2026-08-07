import { renderHook, act } from "@testing-library/react-native";
import { useWorkingTrace, useObservedSequence } from "../BotPrimitives";

/**
 * The trace is what makes the chat look busy while real work happens.
 * These tests pin the two properties that keep it honest:
 *  - it only ever shows stages it was actually given, in order;
 *  - the minimum dwell EXTENDS a fast step so it is readable, and never
 *    truncates a slow one.
 */
describe("useWorkingTrace", () => {
  beforeEach(() => jest.useFakeTimers());
  afterEach(() => jest.useRealTimers());

  function setup(labels: string[], running: boolean) {
    return renderHook(
      ({ l, r }: { l: string[]; r: boolean }) => useWorkingTrace(l, r),
      { initialProps: { l: labels, r: running } },
    );
  }

  it("reveals only the first step immediately, holding the rest back so each is readable", () => {
    const { result } = setup(["Validating your answer…", "Saving your progress…", "Preparing the next question…"], true);

    expect(result.current).toEqual([{ label: "Validating your answer…", status: "pending" }]);
  });

  it("reveals each further step one at a time, settling the one before it", () => {
    const { result } = setup(["Validating your answer…", "Saving your progress…", "Preparing the next question…"], true);

    act(() => { jest.advanceTimersByTime(700); });
    expect(result.current).toEqual([
      { label: "Validating your answer…", status: "done" },
      { label: "Saving your progress…", status: "pending" },
    ]);

    act(() => { jest.advanceTimersByTime(700); });
    expect(result.current).toEqual([
      { label: "Validating your answer…", status: "done" },
      { label: "Saving your progress…", status: "done" },
      { label: "Preparing the next question…", status: "pending" },
    ]);
  });

  it("keeps the last step shimmering while the real work is still running, however long that takes", () => {
    const { result } = setup(["Finding a professional…"], true);

    act(() => { jest.advanceTimersByTime(10_000); });

    // Still pending -- the dwell never settles a step that is genuinely
    // still in flight.
    expect(result.current).toEqual([{ label: "Finding a professional…", status: "pending" }]);
  });

  it("settles the final step once the real work finishes, after its readable moment", () => {
    const { result, rerender } = setup(["Finding a professional…"], true);

    rerender({ l: ["Finding a professional…"], r: false });
    expect(result.current[0].status).toBe("pending");

    act(() => { jest.advanceTimersByTime(700); });
    expect(result.current).toEqual([{ label: "Finding a professional…", status: "done" }]);
  });

  it("starts a fresh trace when a new operation replaces the list, not when one appends", () => {
    const { result, rerender } = setup(["Validating your answer…", "Saving your progress…"], true);
    act(() => { jest.advanceTimersByTime(700); });
    expect(result.current).toHaveLength(2);

    // A brand-new operation -- the controller replaces the array wholesale.
    rerender({ l: ["Understanding your request…"], r: true });
    expect(result.current).toEqual([{ label: "Understanding your request…", status: "pending" }]);
  });

  it("never shows a stage it was not given", () => {
    const { result } = setup(["Saving your progress…"], true);
    expect(result.current.map(e => e.label)).toEqual(["Saving your progress…"]);
  });
});

describe("useObservedSequence", () => {
  it("accumulates distinct consecutive stages and ignores repeats and nulls", () => {
    const { result, rerender } = renderHook(
      ({ s }: { s: string | null }) => useObservedSequence(s),
      { initialProps: { s: "Checking details" as string | null } },
    );

    rerender({ s: "Checking details" });
    rerender({ s: "Confirming availability" });
    rerender({ s: null });

    expect(result.current).toEqual(["Checking details", "Confirming availability"]);
  });
});
