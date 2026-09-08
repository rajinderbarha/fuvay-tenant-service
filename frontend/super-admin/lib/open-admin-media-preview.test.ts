import { afterEach, expect, it, vi } from "vitest";
import { loadAdminDocument } from "./open-admin-media-preview";
afterEach(() => vi.unstubAllGlobals());
it("refuses active HTML content in the document viewer", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, blob: async () => new Blob(["html"], {type: "text/html"}) })));
  await expect(loadAdminDocument("asset")).rejects.toThrow("cannot be previewed safely");
});
it("reports access denial instead of turning an error response into a document", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 403 })));
  await expect(loadAdminDocument("asset")).rejects.toThrow("HTTP 403");
});
