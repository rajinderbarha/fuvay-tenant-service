import { afterEach, expect, it, vi } from "vitest";
import { loadAdminDocument } from "./open-admin-media-preview";
const mock = vi.hoisted(() => ({
  createSignedPreviewUrl: vi.fn(),
  fetchSignedFile: vi.fn(),
}));
vi.mock("./api", () => ({
  mediaAdminApi: {
    createSignedPreviewUrl: mock.createSignedPreviewUrl,
    fetchSignedFile: mock.fetchSignedFile,
  },
}));

afterEach(() => vi.clearAllMocks());

it("refuses active HTML content in the document viewer", async () => {
  mock.createSignedPreviewUrl.mockResolvedValue({ url: "/v1/media/signed/token" });
  mock.fetchSignedFile.mockResolvedValue(new Blob(["html"], {type: "text/html"}));
  await expect(loadAdminDocument("asset")).rejects.toThrow("cannot be previewed safely");
});

it("creates and consumes the authenticated single-use admin preview", async () => {
  const blob = new Blob(["pdf"], {type: "application/pdf"});
  mock.createSignedPreviewUrl.mockResolvedValue({ url: "/v1/media/signed/token" });
  mock.fetchSignedFile.mockResolvedValue(blob);

  await expect(loadAdminDocument("asset")).resolves.toBe(blob);
  expect(mock.createSignedPreviewUrl).toHaveBeenCalledWith("asset");
  expect(mock.fetchSignedFile).toHaveBeenCalledWith("/v1/media/signed/token");
});

it("reports a secure-preview failure instead of treating it as a document", async () => {
  mock.createSignedPreviewUrl.mockRejectedValue(new Error("The secure media link could not be opened."));
  await expect(loadAdminDocument("asset")).rejects.toThrow("secure media link");
});

it("does not create a signed link after the viewer has been closed", async () => {
  const controller = new AbortController();
  controller.abort();
  await expect(loadAdminDocument("asset", controller.signal)).rejects.toMatchObject({ name: "AbortError" });
  expect(mock.createSignedPreviewUrl).not.toHaveBeenCalled();
});
