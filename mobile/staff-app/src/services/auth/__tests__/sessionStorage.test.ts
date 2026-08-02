import * as SecureStore from "expo-secure-store";
import { readSessionBundle, writeSessionBundle, clearSessionBundle } from "../sessionStorage";

beforeEach(() => {
  (SecureStore as any).__resetMockStore();
  jest.clearAllMocks();
});

describe("sessionStorage — SecureStore round trip (spec section 5)", () => {
  it("returns null when nothing is stored", async () => {
    expect(await readSessionBundle()).toBeNull();
  });

  it("writes and reads back a complete bundle", async () => {
    await writeSessionBundle({ schemaVersion: 1, accessToken: "a1", refreshToken: "r1", sessionId: "s1" });
    const bundle = await readSessionBundle();
    expect(bundle).toEqual({ schemaVersion: 1, accessToken: "a1", refreshToken: "r1", sessionId: "s1" });
  });

  it("clears the bundle", async () => {
    await writeSessionBundle({ schemaVersion: 1, accessToken: "a1", refreshToken: "r1", sessionId: null });
    await clearSessionBundle();
    expect(await readSessionBundle()).toBeNull();
  });

  it("treats a corrupt (non-JSON) stored value as absent and clears it", async () => {
    (SecureStore.getItemAsync as jest.Mock).mockResolvedValueOnce("{not json");
    const bundle = await readSessionBundle();
    expect(bundle).toBeNull();
    expect(SecureStore.deleteItemAsync).toHaveBeenCalled();
  });

  it("treats a partial/incomplete bundle (missing refreshToken) as invalid and clears it", async () => {
    (SecureStore.getItemAsync as jest.Mock).mockResolvedValueOnce(JSON.stringify({ schemaVersion: 1, accessToken: "a1" }));
    const bundle = await readSessionBundle();
    expect(bundle).toBeNull();
    expect(SecureStore.deleteItemAsync).toHaveBeenCalled();
  });

  it("treats a bundle from an old/unknown schema version as invalid", async () => {
    (SecureStore.getItemAsync as jest.Mock).mockResolvedValueOnce(JSON.stringify({ schemaVersion: 0, accessToken: "a1", refreshToken: "r1" }));
    expect(await readSessionBundle()).toBeNull();
  });

  it("never returns a partially-restored session on a read failure", async () => {
    (SecureStore.getItemAsync as jest.Mock).mockRejectedValueOnce(new Error("keychain unavailable"));
    expect(await readSessionBundle()).toBeNull();
  });
});
