import { getOrCreateIdempotencyKey, clearIdempotencyKey } from "../idempotencyStore";

describe("idempotency store", () => {
  it("returns the same key for a retry of the same operation scope", async () => {
    const k1 = await getOrCreateIdempotencyKey("quote-approve:quote-1");
    const k2 = await getOrCreateIdempotencyKey("quote-approve:quote-1");
    expect(k1).toBe(k2);
  });

  it("never reuses a key across different operation scopes (different quote IDs)", async () => {
    const k1 = await getOrCreateIdempotencyKey("quote-approve:quote-1");
    const k2 = await getOrCreateIdempotencyKey("quote-approve:quote-2");
    expect(k1).not.toBe(k2);
  });

  it("clearing a scope's key produces a fresh key on the next call", async () => {
    const k1 = await getOrCreateIdempotencyKey("quote-approve:quote-3");
    await clearIdempotencyKey("quote-approve:quote-3");
    const k2 = await getOrCreateIdempotencyKey("quote-approve:quote-3");
    expect(k1).not.toBe(k2);
  });

  it("generates a fresh key once the TTL has elapsed", async () => {
    const k1 = await getOrCreateIdempotencyKey("quote-approve:quote-4", -1);
    const k2 = await getOrCreateIdempotencyKey("quote-approve:quote-4", -1);
    expect(k1).not.toBe(k2);
  });
});
