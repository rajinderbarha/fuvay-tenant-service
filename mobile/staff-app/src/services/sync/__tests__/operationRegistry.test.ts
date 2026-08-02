import { classify, isTransientFailure, isPermanentFailure, OPERATION_REGISTRY } from "../operationRegistry";

describe("operationRegistry (Phase Z)", () => {
  it("classifies every registered operation into one of the four explicit classes", () => {
    const validClasses = new Set(["LOCAL_DRAFT", "MEDIA_UPLOAD", "IDEMPOTENT_MUTATION", "ONLINE_ONLY_MUTATION"]);
    Object.values(OPERATION_REGISTRY).forEach(def => {
      expect(validClasses.has(def.operation_class)).toBe(true);
    });
  });

  it("classifies media uploads distinctly from idempotent mutations", () => {
    expect(classify("INSPECTION_PHOTO_UPLOAD").operation_class).toBe("MEDIA_UPLOAD");
    expect(classify("DOCUMENT_UPLOAD").operation_class).toBe("MEDIA_UPLOAD");
    expect(classify("WORK_FINISH").operation_class).toBe("IDEMPOTENT_MUTATION");
  });

  it("classifies support-request creation as a local draft (compose offline, submit online)", () => {
    expect(classify("SUPPORT_REQUEST_CREATE").operation_class).toBe("LOCAL_DRAFT");
  });

  it("never treats validation/permission/conflict errors as transient", () => {
    expect(isTransientFailure("VALIDATION_ERROR")).toBe(false);
    expect(isTransientFailure("ACTION_NOT_ALLOWED")).toBe(false);
    expect(isTransientFailure("STALE_ENTITY_VERSION")).toBe(false);
    expect(isPermanentFailure("VALIDATION_ERROR")).toBe(true);
    expect(isPermanentFailure("STALE_ENTITY_VERSION")).toBe(true);
  });

  it("treats only timeout/server-unavailable/rate-limited as transient", () => {
    expect(isTransientFailure("NETWORK_TIMEOUT")).toBe(true);
    expect(isTransientFailure("SERVER_UNAVAILABLE")).toBe(true);
    expect(isTransientFailure("RATE_LIMITED")).toBe(true);
  });
});
