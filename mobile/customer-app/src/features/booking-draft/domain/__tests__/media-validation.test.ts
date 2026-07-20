import { validateMediaCandidate, MAX_BOOKING_PHOTO_SIZE_BYTES, MAX_BOOKING_PHOTOS_PER_DRAFT } from "../media-validation";

const validCandidate = { uri: "file:///tmp/a.jpg", mimeType: "image/jpeg", fileSizeBytes: 1024 };

describe("validateMediaCandidate", () => {
  it("accepts a valid jpeg under the size limit", () => {
    expect(validateMediaCandidate(validCandidate, 0)).toBeNull();
  });

  it("rejects a missing URI", () => {
    expect(validateMediaCandidate({ ...validCandidate, uri: "" }, 0)).toBe("MISSING_URI");
  });

  it("rejects gif even though the underlying media engine allows it (stricter draft-linking rule)", () => {
    expect(validateMediaCandidate({ ...validCandidate, mimeType: "image/gif" }, 0)).toBe("UNSUPPORTED_TYPE");
  });

  it("rejects an unsupported MIME type", () => {
    expect(validateMediaCandidate({ ...validCandidate, mimeType: "application/pdf" }, 0)).toBe("UNSUPPORTED_TYPE");
  });

  it("rejects a null MIME type (fails closed rather than assuming a safe type)", () => {
    expect(validateMediaCandidate({ ...validCandidate, mimeType: null }, 0)).toBe("UNSUPPORTED_TYPE");
  });

  it("rejects a file over the real 10MB limit", () => {
    expect(validateMediaCandidate({ ...validCandidate, fileSizeBytes: MAX_BOOKING_PHOTO_SIZE_BYTES + 1 }, 0)).toBe("TOO_LARGE");
  });

  it("accepts a file exactly at the limit", () => {
    expect(validateMediaCandidate({ ...validCandidate, fileSizeBytes: MAX_BOOKING_PHOTO_SIZE_BYTES }, 0)).toBeNull();
  });

  it("does not fail size validation when file size is unknown (post-compression)", () => {
    expect(validateMediaCandidate({ ...validCandidate, fileSizeBytes: null }, 0)).toBeNull();
  });

  it("rejects once the real 5-photo draft limit is reached", () => {
    expect(validateMediaCandidate(validCandidate, MAX_BOOKING_PHOTOS_PER_DRAFT)).toBe("COUNT_LIMIT_REACHED");
  });

  it("accepts the last allowed slot", () => {
    expect(validateMediaCandidate(validCandidate, MAX_BOOKING_PHOTOS_PER_DRAFT - 1)).toBeNull();
  });
});
