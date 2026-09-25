import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const root = resolve(__dirname, "../../..");

describe("global provider job alerts", () => {
  it("mounts once in the authenticated tenant layout, not only the dashboard", () => {
    const layout = readFileSync(resolve(root, "app/(tenant)/layout.tsx"), "utf8");
    const dashboard = readFileSync(resolve(root, "app/(tenant)/dashboard/page.tsx"), "utf8");
    expect(layout).toContain("<GlobalJobAlerts />");
    expect(layout.indexOf("<GlobalJobAlerts />")).toBeGreaterThan(layout.indexOf("<RequireSession>"));
    expect(dashboard).not.toContain("<JobAlertPopup");
  });
});
