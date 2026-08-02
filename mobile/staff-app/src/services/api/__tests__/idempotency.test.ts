import { IdempotencyKeyStore, generateIdempotencyKey } from "../idempotency";

describe("generateIdempotencyKey", () => {
  it("generates a UUID-shaped key", () => {
    expect(generateIdempotencyKey()).toMatch(/^[0-9a-f-]{36}$/i);
  });

  it("never repeats across calls", () => {
    const a = generateIdempotencyKey();
    const b = generateIdempotencyKey();
    expect(a).not.toBe(b);
  });
});

describe("IdempotencyKeyStore", () => {
  it("returns the SAME key for the same intent on repeated calls (retry of the same user action)", () => {
    const store = new IdempotencyKeyStore();
    const first = store.getOrCreateKey("job:j1:start-work");
    const second = store.getOrCreateKey("job:j1:start-work");
    expect(first).toBe(second);
  });

  it("returns a DIFFERENT key for a different intent", () => {
    const store = new IdempotencyKeyStore();
    const a = store.getOrCreateKey("job:j1:start-work");
    const b = store.getOrCreateKey("job:j2:start-work");
    expect(a).not.toBe(b);
  });

  it("newIntent always mints a fresh key even for the same intent id (an explicit new user action)", () => {
    const store = new IdempotencyKeyStore();
    const first = store.getOrCreateKey("job:j1:start-work");
    const second = store.newIntent("job:j1:start-work");
    expect(first).not.toBe(second);
    // subsequent getOrCreateKey for the same intent now returns the NEW key
    expect(store.getOrCreateKey("job:j1:start-work")).toBe(second);
  });

  it("clearIntent removes the stored key so the next call mints a new one", () => {
    const store = new IdempotencyKeyStore();
    const first = store.getOrCreateKey("job:j1:start-work");
    store.clearIntent("job:j1:start-work");
    const second = store.getOrCreateKey("job:j1:start-work");
    expect(first).not.toBe(second);
  });
});
