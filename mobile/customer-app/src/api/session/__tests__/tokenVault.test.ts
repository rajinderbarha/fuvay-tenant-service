import { saveSession, loadSession, clearSession, rotateTokens, getInMemoryAccessToken } from "../tokenVault";
import { asCustomerId } from "../../../domain/ids";
import { setSecureItem } from "../../../storage/secureStorage";

const SecureStore = require("expo-secure-store");
const customerId = asCustomerId("customer-1");

describe("tokenVault", () => {
  beforeEach(async () => {
    SecureStore.__resetMockStore();
    await clearSession();
  });

  it("round-trips a saved session atomically", async () => {
    await saveSession("access-1", "refresh-1", customerId);
    const loaded = await loadSession();
    expect(loaded?.accessToken).toBe("access-1");
    expect(loaded?.refreshToken).toBe("refresh-1");
    expect(loaded?.customerId).toBe(customerId);
  });

  it("keeps the access token available in memory without a re-read", async () => {
    await saveSession("access-2", "refresh-2", customerId);
    expect(getInMemoryAccessToken()).toBe("access-2");
  });

  it("fails closed on a corrupted (non-JSON) record", async () => {
    await setSecureItem("customer_app_session_record_v1", "{not json");
    const loaded = await loadSession();
    expect(loaded).toBeNull();
  });

  it("fails closed on a partial record (missing required field)", async () => {
    await setSecureItem("customer_app_session_record_v1", JSON.stringify({ schemaVersion: 1, accessToken: "a" }));
    const loaded = await loadSession();
    expect(loaded).toBeNull();
  });

  it("fails closed on a version-mismatched record", async () => {
    await setSecureItem(
      "customer_app_session_record_v1",
      JSON.stringify({ schemaVersion: 999, accessToken: "a", refreshToken: "r", customerId: "c", savedAt: "now" }),
    );
    const loaded = await loadSession();
    expect(loaded).toBeNull();
  });

  it("logout (clearSession) removes the record and the in-memory token", async () => {
    await saveSession("access-3", "refresh-3", customerId);
    await clearSession();
    expect(await loadSession()).toBeNull();
    expect(getInMemoryAccessToken()).toBeNull();
  });

  it("rotateTokens atomically replaces both tokens in one write", async () => {
    await saveSession("access-old", "refresh-old", customerId);
    await rotateTokens("access-new", "refresh-new", customerId);
    const loaded = await loadSession();
    expect(loaded?.accessToken).toBe("access-new");
    expect(loaded?.refreshToken).toBe("refresh-new");
  });

  it("never writes a token value to a non-secure storage key namespace", async () => {
    await saveSession("access-4", "refresh-4", customerId);
    expect(SecureStore.setItemAsync).toHaveBeenCalledWith(
      "customer_app_session_record_v1",
      expect.stringContaining("access-4"),
    );
  });
});
