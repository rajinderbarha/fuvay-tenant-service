import "@testing-library/jest-dom/vitest";

// jsdom does not implement ResizeObserver, but recharts' <ResponsiveContainer>
// (used by several dashboard widgets under test) requires it to observe its
// container element. Without this mock, any test that renders a chart throws
// "ReferenceError: ResizeObserver is not defined" in jsdom's test environment
// even though the real browser DOM provides it. This is a test-environment
// gap, not a product bug.
if (typeof globalThis.ResizeObserver === "undefined") {
  class ResizeObserverMock {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  globalThis.ResizeObserver = ResizeObserverMock as unknown as typeof ResizeObserver;
}
