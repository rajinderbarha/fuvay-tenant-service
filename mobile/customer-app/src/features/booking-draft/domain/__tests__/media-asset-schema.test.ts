import { parseUploadResponse, parseMediaAsset, parseMediaAssetList, parseReplaceResponse, parseDeleteResponse } from "../media-asset-schema";

const validAsset = {
  id: "asset-1",
  owner_type: "booking_draft",
  owner_id: "draft-1",
  tenant_id: null,
  customer_id: "cust-1",
  uploaded_by_user_id: "cust-1",
  media_context: "booking_issue_photo",
  file_name_original: "photo.jpg",
  mime_type: "image/jpeg",
  file_extension: ".jpg",
  file_size_bytes: 123456,
  storage_driver: "local",
  is_public: false,
  access_level: "customer",
  status: "active",
  width: 1200,
  height: 900,
  preview_url: "/v1/media/asset-1/view",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("parseUploadResponse", () => {
  it("unwraps the real nested {success, data} envelope unique to the upload endpoint", () => {
    const parsed = parseUploadResponse({ success: true, data: validAsset });
    expect(parsed?.id).toBe("asset-1");
  });

  it("returns null when the outer envelope is missing", () => {
    expect(parseUploadResponse(validAsset)).toBeNull();
  });
});

describe("parseMediaAsset", () => {
  it("accepts a well-formed asset (flat, not wrapped)", () => {
    expect(parseMediaAsset(validAsset)).toEqual(validAsset);
  });

  it("rejects a malformed payload", () => {
    expect(parseMediaAsset(null)).toBeNull();
  });
});

describe("parseMediaAssetList", () => {
  it("accepts a well-formed list envelope", () => {
    const result = parseMediaAssetList({ items: [validAsset], total: 1, page: 1, page_size: 25 });
    expect(result?.items).toHaveLength(1);
    expect(result?.droppedCount).toBe(0);
  });

  it("drops an individually-invalid item without failing the whole list", () => {
    const { id, ...invalid } = validAsset;
    void id;
    const result = parseMediaAssetList({ items: [validAsset, invalid], total: 2, page: 1, page_size: 25 });
    expect(result?.items).toHaveLength(1);
    expect(result?.droppedCount).toBe(1);
  });
});

describe("parseReplaceResponse", () => {
  it("accepts the real {replaced_id, new_asset} shape", () => {
    const result = parseReplaceResponse({ replaced_id: "asset-1", new_asset: { ...validAsset, id: "asset-2" } });
    expect(result?.replacedId).toBe("asset-1");
    expect(result?.newAsset.id).toBe("asset-2");
  });
});

describe("parseDeleteResponse", () => {
  it("accepts the real {id, deleted} shape", () => {
    expect(parseDeleteResponse({ id: "asset-1", deleted: true })).toEqual({ id: "asset-1", deleted: true });
  });
});
