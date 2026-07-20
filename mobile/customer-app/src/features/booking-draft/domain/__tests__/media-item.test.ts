import {
  createMediaItem,
  markInvalid,
  markUploading,
  markUploadFailed,
  markUploaded,
  markLinking,
  markLinkFailed,
  markLinked,
  markDeleting,
  markDeleted,
  isRetryable,
  isTerminal,
  canRetry,
} from "../media-item";

describe("media item state machine", () => {
  it("starts SELECTED", () => {
    const item = createMediaItem("l1", "file://x.jpg", "image/jpeg", 100);
    expect(item.status).toBe("SELECTED");
  });

  it("moves through the real upload/link happy path", () => {
    let item = createMediaItem("l1", "file://x.jpg", "image/jpeg", 100);
    item = markUploading(item);
    expect(item.status).toBe("UPLOADING");
    item = markUploaded(item, "asset-1");
    expect(item.status).toBe("UPLOADED");
    expect(item.mediaAssetId).toBe("asset-1");
    item = markLinking(item);
    expect(item.status).toBe("LINKING");
    item = markLinked(item);
    expect(item.status).toBe("LINKED");
    expect(isTerminal(item)).toBe(true);
  });

  it("marks invalid items terminal without an upload attempt", () => {
    const item = markInvalid(createMediaItem("l1", "file://x.jpg", "image/gif", 100), "UNSUPPORTED_TYPE");
    expect(item.status).toBe("INVALID");
    expect(isTerminal(item)).toBe(true);
    expect(isRetryable(item)).toBe(false);
  });

  it("increments retryCount on upload and link failure", () => {
    let item = createMediaItem("l1", "file://x.jpg", "image/jpeg", 100);
    item = markUploadFailed(item, "network_error");
    expect(item.status).toBe("UPLOAD_FAILED");
    expect(item.retryCount).toBe(1);
    expect(isRetryable(item)).toBe(true);

    item = markLinkFailed(item, "server_error");
    expect(item.status).toBe("LINK_FAILED");
    expect(item.retryCount).toBe(2);
  });

  it("caps retries so an item does not retry forever", () => {
    let item = createMediaItem("l1", "file://x.jpg", "image/jpeg", 100);
    for (let i = 0; i < 3; i++) item = markUploadFailed(item, "network_error");
    expect(canRetry(item)).toBe(false);
  });

  it("allows retry while under the cap", () => {
    let item = createMediaItem("l1", "file://x.jpg", "image/jpeg", 100);
    item = markUploadFailed(item, "network_error");
    expect(canRetry(item)).toBe(true);
  });

  it("moves through the delete path", () => {
    let item = markLinked(markLinking(markUploaded(markUploading(createMediaItem("l1", "file://x.jpg", "image/jpeg", 100)), "asset-1")));
    item = markDeleting(item);
    expect(item.status).toBe("DELETING");
    item = markDeleted(item);
    expect(item.status).toBe("DELETED");
    expect(isTerminal(item)).toBe(true);
  });
});
