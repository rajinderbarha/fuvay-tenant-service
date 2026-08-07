import { resolveMediaUrl } from "../mediaUrl";
import { ENV } from "../../config/environment";

describe("resolveMediaUrl", () => {
  it("absolutises the server-relative path the media engine returns", () => {
    // The local storage driver returns e.g. "/uploads/category_icon/x.png".
    // React Native has no page origin, so a relative URI never loads -- this
    // is exactly why admin-uploaded category artwork rendered as blank space
    // (the built-in glyph fallback only triggers on a null URL, not a
    // broken one, so nothing was drawn at all).
    expect(resolveMediaUrl("/uploads/category_icon/x.png"))
      .toBe(`${ENV.apiBaseUrl}/uploads/category_icon/x.png`);
  });

  it("adds the missing separator for a path without a leading slash", () => {
    expect(resolveMediaUrl("uploads/x.png")).toBe(`${ENV.apiBaseUrl}/uploads/x.png`);
  });

  it("passes absolute and data URLs through untouched", () => {
    // Cloudinary/S3 drivers already return absolute URLs.
    expect(resolveMediaUrl("https://cdn.example.com/a.png")).toBe("https://cdn.example.com/a.png");
    expect(resolveMediaUrl("//cdn.example.com/a.png")).toBe("//cdn.example.com/a.png");
    expect(resolveMediaUrl("data:image/png;base64,AAAA")).toBe("data:image/png;base64,AAAA");
  });

  it("returns null for absent or blank input so callers fall back to a glyph", () => {
    expect(resolveMediaUrl(null)).toBeNull();
    expect(resolveMediaUrl(undefined)).toBeNull();
    expect(resolveMediaUrl("   ")).toBeNull();
  });
});
