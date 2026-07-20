import { draftQueryKeys } from "../draft-queries";
import { mediaQueryKeys } from "../media-queries";

describe("draftQueryKeys.detail", () => {
  it("is scoped by draftId, locale and tenant", () => {
    expect(draftQueryKeys.detail("draft-1", "en", "tenant-1")).toEqual(["bookingDraft", "detail", "draft-1", "en", "tenant-1"]);
  });

  it("uses a stable placeholder for an absent tenant", () => {
    expect(draftQueryKeys.detail("draft-1", "en", undefined)).toEqual(["bookingDraft", "detail", "draft-1", "en", "no-tenant"]);
  });

  it("produces distinct keys for different drafts", () => {
    expect(draftQueryKeys.detail("draft-1", "en", undefined)).not.toEqual(draftQueryKeys.detail("draft-2", "en", undefined));
  });
});

describe("mediaQueryKeys.draftMedia", () => {
  it("is scoped by draftId, locale and tenant", () => {
    expect(mediaQueryKeys.draftMedia("draft-1", "en", "tenant-1")).toEqual(["bookingMedia", "list", "draft-1", "en", "tenant-1"]);
  });

  it("produces distinct keys for different drafts (no cross-draft media leakage in cache)", () => {
    expect(mediaQueryKeys.draftMedia("draft-1", "en", undefined)).not.toEqual(mediaQueryKeys.draftMedia("draft-2", "en", undefined));
  });
});
