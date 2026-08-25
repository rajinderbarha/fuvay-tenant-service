import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { validateImageFile, CROP_PRESETS } from "../ImageCropModal";

/**
 * The picker rules are the only place a bad photo gets stopped before it costs
 * a round trip, so they are worth pinning down: they must reject exactly what
 * the media engine's CONTEXT_RULES would reject, plus sources too small to
 * crop without visible upscaling.
 */

const RealImage = globalThis.Image;

/** Stubs image decoding so a fake File can report chosen dimensions. */
function stubDecode(dims: { width: number; height: number } | null) {
  class FakeImage {
    onload: (() => void) | null = null;
    onerror: (() => void) | null = null;
    naturalWidth = dims?.width ?? 0;
    naturalHeight = dims?.height ?? 0;
    set src(_v: string) {
      queueMicrotask(() => (dims ? this.onload?.() : this.onerror?.()));
    }
  }
  globalThis.Image = FakeImage as unknown as typeof Image;
}

function fakeFile(type: string, sizeBytes: number): File {
  const file = new File(["x"], "photo.jpg", { type });
  Object.defineProperty(file, "size", { value: sizeBytes });
  return file;
}

const MB = 1024 * 1024;

beforeEach(() => {
  globalThis.URL.createObjectURL = vi.fn(() => "blob:stub");
  globalThis.URL.revokeObjectURL = vi.fn();
});
afterEach(() => {
  globalThis.Image = RealImage;
  vi.restoreAllMocks();
});

describe("validateImageFile", () => {
  it("accepts a JPG that clears every rule", async () => {
    stubDecode({ width: 1200, height: 1200 });
    const result = await validateImageFile(fakeFile("image/jpeg", 2 * MB), CROP_PRESETS.avatar);
    expect(result.ok).toBe(true);
    expect(result.width).toBe(1200);
  });

  it("accepts PNG and WebP as well as JPG", async () => {
    stubDecode({ width: 600, height: 600 });
    for (const type of ["image/png", "image/webp"]) {
      const result = await validateImageFile(fakeFile(type, MB), CROP_PRESETS.avatar);
      expect(result.ok, type).toBe(true);
    }
  });

  it("rejects a non-image type without attempting to decode it", async () => {
    stubDecode({ width: 4000, height: 4000 });
    const result = await validateImageFile(fakeFile("application/pdf", MB), CROP_PRESETS.avatar);
    expect(result.ok).toBe(false);
    expect(result.error).toMatch(/JPG, PNG or WebP/);
  });

  it("rejects animated GIF, which cannot survive a crop", async () => {
    stubDecode({ width: 800, height: 800 });
    const result = await validateImageFile(fakeFile("image/gif", MB), CROP_PRESETS.avatar);
    expect(result.ok).toBe(false);
  });

  it("enforces the 5 MB ceiling on avatars and reports the actual size", async () => {
    stubDecode({ width: 4000, height: 4000 });
    const result = await validateImageFile(fakeFile("image/jpeg", 6 * MB), CROP_PRESETS.avatar);
    expect(result.ok).toBe(false);
    expect(result.error).toContain("6.0 MB");
    expect(result.error).toContain("maximum is 5 MB");
  });

  it("allows a cover photo up to its higher 10 MB ceiling", async () => {
    stubDecode({ width: 1800, height: 600 });
    const ok = await validateImageFile(fakeFile("image/jpeg", 8 * MB), CROP_PRESETS.cover);
    expect(ok.ok).toBe(true);

    const tooBig = await validateImageFile(fakeFile("image/jpeg", 11 * MB), CROP_PRESETS.cover);
    expect(tooBig.ok).toBe(false);
  });

  it("rejects a source too small to crop sharply", async () => {
    stubDecode({ width: 120, height: 120 });
    const result = await validateImageFile(fakeFile("image/jpeg", MB), CROP_PRESETS.avatar);
    expect(result.ok).toBe(false);
    expect(result.error).toContain("120x120px");
    expect(result.error).toContain("at least 200x200px");
  });

  it("applies the cover's wider minimum independently of the avatar's", async () => {
    stubDecode({ width: 400, height: 400 });
    // Comfortably passes the avatar rule...
    expect((await validateImageFile(fakeFile("image/jpeg", MB), CROP_PRESETS.avatar)).ok).toBe(true);
    // ...but is far too narrow for a 3:1 banner.
    expect((await validateImageFile(fakeFile("image/jpeg", MB), CROP_PRESETS.cover)).ok).toBe(false);
  });

  it("reports a corrupted image instead of passing it through to upload", async () => {
    stubDecode(null);
    const result = await validateImageFile(fakeFile("image/jpeg", MB), CROP_PRESETS.avatar);
    expect(result.ok).toBe(false);
    expect(result.error).toMatch(/could not be read/);
  });
});
