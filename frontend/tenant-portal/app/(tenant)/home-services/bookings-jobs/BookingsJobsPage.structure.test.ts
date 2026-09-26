import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const source = readFileSync(resolve(__dirname, "BookingsJobsPage.tsx"), "utf8");

describe("Bookings & Jobs view preference", () => {
  it("uses cards by default and makes board mode explicitly URL-driven", () => {
    expect(source).toContain('searchParams.get("view") === "board" ? "board" : "cards"');
    expect(source).toContain('updateParams({ view: null })');
    expect(source).toContain('updateParams({ view: "board" })');
    expect(source).not.toContain('useState<"cards" | "board">');
  });
});
