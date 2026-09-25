import { describe, expect, it } from "vitest";

import type { DashboardAlert } from "../lib/api";
import { alertKey } from "./useJobAlerts";

const delayed = (minutes: number, label: string): DashboardAlert => ({
  job_id: "job-1",
  label: "JOB-1",
  city: "Bassi Pathana",
  tone: "warning",
  title: "Job past its slot",
  message: `${label}.`,
  alert_kind: "delayed",
  minutes_late: minutes,
  lateness_label: label,
});

describe("provider alert deduplication", () => {
  it("does not treat each changing minute label as a new popup", () => {
    expect(alertKey(delayed(21, "21 min late"))).toBe(alertKey(delayed(22, "22 min late")));
  });

  it("creates a new alert only at a meaningful delay milestone", () => {
    expect(alertKey(delayed(59, "59 min late"))).not.toBe(alertKey(delayed(60, "1 hour late")));
    expect(alertKey(delayed(239, "3 hours late"))).not.toBe(alertKey(delayed(240, "4 hours late")));
  });

  it("re-alerts an assignment when it escalates to overdue", () => {
    const offer: DashboardAlert = {
      ...delayed(0, ""), alert_kind: "assignment", assignment_required: true,
      assignment_overdue: false,
    };
    expect(alertKey(offer)).not.toBe(alertKey({ ...offer, assignment_overdue: true }));
  });
});
