import { renderHook } from "@testing-library/react-native";
import { useWorkingTrace } from "../BotPrimitives";

/**
 * The trace is what makes the chat look "busy" while real work happens.
 * These tests pin the one property that keeps it honest: a line only ever
 * settles to "done" because the caller genuinely moved on -- never on a
 * timer -- so a slow backend call keeps shimmering for as long as it
 * actually takes.
 */
describe("useWorkingTrace", () => {
  it("starts empty and shows the first real stage as still running", () => {
    const { result, rerender } = renderHook(({ label }: { label: string | null }) => useWorkingTrace(label), {
      initialProps: { label: null as string | null },
    });
    expect(result.current).toEqual([]);

    rerender({ label: "Checking your booking details…" });
    expect(result.current).toEqual([{ label: "Checking your booking details…", status: "pending" }]);
  });

  it("accumulates stages, settling each earlier one only when the next actually begins", () => {
    const { result, rerender } = renderHook(({ label }: { label: string | null }) => useWorkingTrace(label), {
      initialProps: { label: "Checking details" as string | null },
    });
    rerender({ label: "Confirming availability" });

    expect(result.current).toEqual([
      { label: "Checking details", status: "done" },
      { label: "Confirming availability", status: "pending" },
    ]);
  });

  it("keeps a stage pending across re-renders while it is genuinely still running", () => {
    const { result, rerender } = renderHook(({ label }: { label: string | null }) => useWorkingTrace(label), {
      initialProps: { label: "Finding a professional" as string | null },
    });
    rerender({ label: "Finding a professional" });
    rerender({ label: "Finding a professional" });

    // Still one entry, still running -- no timer settled it early.
    expect(result.current).toEqual([{ label: "Finding a professional", status: "pending" }]);
  });

  it("settles every remaining stage once the sequence finishes", () => {
    const { result, rerender } = renderHook(({ label }: { label: string | null }) => useWorkingTrace(label), {
      initialProps: { label: "Checking details" as string | null },
    });
    rerender({ label: "Preparing your review" });
    rerender({ label: null });

    expect(result.current).toEqual([
      { label: "Checking details", status: "done" },
      { label: "Preparing your review", status: "done" },
    ]);
  });

  it("leaves the settled trace on screen after completion instead of clearing it", () => {
    const { result, rerender } = renderHook(({ label }: { label: string | null }) => useWorkingTrace(label), {
      initialProps: { label: "Checking details" as string | null },
    });
    rerender({ label: null });
    rerender({ label: null });

    expect(result.current).toHaveLength(1);
    expect(result.current[0].status).toBe("done");
  });
});
