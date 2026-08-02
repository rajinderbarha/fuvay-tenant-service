import { parseDeepLink, setPendingDeepLink, consumePendingDeepLink } from "../deepLinking";

describe("parseDeepLink — allow-listed custom scheme", () => {
  it("parses a cold-start top-level link", () => {
    expect(parseDeepLink("serviceos://jobs")).toEqual({ routeKey: "JOBS" });
  });

  it("parses a job detail link", () => {
    expect(parseDeepLink("serviceos://jobs/j-123")).toEqual({ routeKey: "JOB_DETAIL", jobId: "j-123" });
  });

  it("parses a job sub-route link", () => {
    expect(parseDeepLink("serviceos://jobs/j-123/inspection")).toEqual({ routeKey: "JOB_INSPECTION", jobId: "j-123" });
  });

  it("parses every documented job sub-route", () => {
    expect(parseDeepLink("serviceos://jobs/j1/estimate")?.routeKey).toBe("JOB_ESTIMATE");
    expect(parseDeepLink("serviceos://jobs/j1/parts")?.routeKey).toBe("JOB_PARTS");
    expect(parseDeepLink("serviceos://jobs/j1/checklist")?.routeKey).toBe("JOB_CHECKLIST");
    expect(parseDeepLink("serviceos://jobs/j1/completion")?.routeKey).toBe("JOB_COMPLETION");
  });

  it("parses notifications and profile links", () => {
    expect(parseDeepLink("serviceos://notifications")).toEqual({ routeKey: "NOTIFICATIONS" });
    expect(parseDeepLink("serviceos://profile")).toEqual({ routeKey: "PROFILE" });
  });

  it("fails closed (returns null) for an unknown job sub-route", () => {
    expect(parseDeepLink("serviceos://jobs/j1/not-a-real-subroute")).toBeNull();
  });

  it("fails closed for an unknown top-level path", () => {
    expect(parseDeepLink("serviceos://not-a-real-route")).toBeNull();
  });

  it("fails closed for a malformed URL", () => {
    expect(parseDeepLink("not a url at all")).toBeNull();
  });

  it("fails closed for an empty path", () => {
    expect(parseDeepLink("serviceos://")).toBeNull();
  });

  it("never treats an arbitrary external https URL as an internal route (no universal-link host configured in tests)", () => {
    expect(parseDeepLink("https://evil.example.com/jobs/j1")).toBeNull();
    expect(parseDeepLink("https://serviceos.com/jobs/j1")).toBeNull();
  });

  it("rejects an unsupported scheme outright", () => {
    expect(parseDeepLink("http://serviceos/jobs")).toBeNull();
    expect(parseDeepLink("javascript:alert(1)")).toBeNull();
  });
});

describe("pending deep link — consume-once semantics", () => {
  afterEach(() => { consumePendingDeepLink(); });

  it("stores and returns a pending link exactly once (auth-required pending deep link)", () => {
    setPendingDeepLink({ routeKey: "JOB_DETAIL", jobId: "j1" });
    expect(consumePendingDeepLink()).toEqual({ routeKey: "JOB_DETAIL", jobId: "j1" });
    // Second read must not replay the same navigation.
    expect(consumePendingDeepLink()).toBeNull();
  });

  it("returns null when nothing is pending", () => {
    expect(consumePendingDeepLink()).toBeNull();
  });
});
