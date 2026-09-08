import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ProviderDocuments } from "./ProviderDocuments";
const mock = vi.hoisted(() => ({ load: vi.fn() }));
vi.mock("../../lib/open-admin-media-preview", () => ({ loadAdminDocument: mock.load }));
const doc = { id: "doc", doc_type: "gst_certificate", media_asset_id: "asset", status: "pending_review", version: 2, uploaded_at: "2026-09-08T10:00:00Z" };
beforeEach(() => {
  vi.clearAllMocks();
  URL.createObjectURL = vi.fn(() => "blob:preview");
  URL.revokeObjectURL = vi.fn();
  mock.load.mockResolvedValue(new Blob(["pdf"], { type: "application/pdf" }));
});
afterEach(cleanup);
it("shows version and status and opens a labelled PDF preview inside a dialog", async () => {
  const { unmount } = render(<ProviderDocuments documents={[doc]}/>);
  expect(screen.getByText(/Version 2/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "View gst certificate" }));
  expect(await screen.findByTitle("gst certificate preview")).toHaveAttribute("src", "blob:preview");
  expect(screen.getByRole("link", { name: "Open full size" })).toHaveAttribute("rel", "noopener noreferrer");
  expect(mock.load).toHaveBeenCalledWith("asset", expect.any(AbortSignal));
  unmount();
  expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:preview");
});
it("offers retry when authenticated document loading fails", async () => {
  mock.load.mockRejectedValueOnce(new Error("Document service returned HTTP 403."));
  render(<ProviderDocuments documents={[doc]}/>);
  fireEvent.click(screen.getByRole("button", { name: "View gst certificate" }));
  await screen.findByText("Document service returned HTTP 403.");
  fireEvent.click(screen.getByRole("button", { name: "Retry preview" }));
  await screen.findByTitle("gst certificate preview");
});
it("renders image documents and describes unlinked legacy attachments honestly", async () => {
  mock.load.mockResolvedValue(new Blob(["png"], { type: "image/png" }));
  render(<ProviderDocuments documents={[doc, { ...doc, id: "legacy", media_asset_id: null }]}/>);
  expect(screen.getByText(/No previewable attachment linked/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "View gst certificate" }));
  expect(await screen.findByRole("img", { name: "gst certificate" })).toHaveAttribute("src", "blob:preview");
});
