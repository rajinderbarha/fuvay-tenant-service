/**
 * UX-06 Round 5 — a real, mechanical guard against internal readiness
 * jargon / error codes leaking into customer-facing screen source (the exact
 * class of bug UX-05C found and fixed for MOCK_DESIGN_ONLY leaking into
 * production copy). Scans the actual screen files' string literals, not a
 * mock — a real regression here means an internal label WILL render.
 */
import fs from "fs";
import path from "path";

const SCREENS_DIR = path.resolve(__dirname, "../../screens");
const FORBIDDEN = [
  "MOCK_DESIGN_ONLY", "API_CONTRACT_REQUIRED", "PRICE_OPTIONS_UNAVAILABLE",
  "BargainRule", "HOME_BOOKING_NO_PROVIDER_AVAILABLE", "FINAL_DRAFT_NOT_READY",
  "tenant_service_area", "master_service_id",
];

describe("No internal readiness/error-code jargon in customer-facing screens", () => {
  const files = fs.readdirSync(SCREENS_DIR).filter(f => f.endsWith(".tsx"));

  it("scans every screen file (sanity check the scan itself runs)", () => {
    expect(files.length).toBeGreaterThan(10);
  });

  it.each(files)("%s contains no forbidden internal jargon string", (file) => {
    const contents = fs.readFileSync(path.join(SCREENS_DIR, file), "utf8");
    for (const term of FORBIDDEN) {
      // Comments are allowed to reference these terms for documentation
      // purposes (e.g. explaining why an error is caught) -- only flag the
      // term if it appears OUTSIDE a comment line, i.e. in a string literal
      // a customer could plausibly see rendered.
      const codeLines = contents.split("\n").filter(l => !l.trim().startsWith("//") && !l.trim().startsWith("*"));
      const codeOnly = codeLines.join("\n");
      expect(codeOnly.includes(term)).toBe(false);
    }
  });
});
