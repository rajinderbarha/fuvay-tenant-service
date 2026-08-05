import * as secureStorage from "../secureStorage";
import * as localStorage from "../localStorage";

jest.mock("expo-secure-store", () => ({
  setItemAsync: jest.fn().mockResolvedValue(undefined),
  getItemAsync: jest.fn().mockResolvedValue(null),
  deleteItemAsync: jest.fn().mockResolvedValue(undefined),
}));

describe("storage separation", () => {
  it("keeps secure storage and local storage as distinct modules with distinct keys", () => {
    expect(secureStorage.SecureStorageKeys.accessToken).not.toBe(undefined);
    // localStorage exposes no token-shaped keys -- it is preference/draft
    // storage only, so there is nothing named like a token constant here.
    expect((localStorage as Record<string, unknown>).SecureStorageKeys).toBeUndefined();
  });

  it("secureStorage delegates to expo-secure-store, not AsyncStorage", async () => {
    const SecureStore = require("expo-secure-store");
    await secureStorage.setSecureItem("k", "v");
    expect(SecureStore.setItemAsync).toHaveBeenCalledWith("k", "v");
  });

  it("localStorage round-trips JSON via AsyncStorage", async () => {
    await localStorage.setLocalJSON("draft", { step: 1 });
    const value = await localStorage.getLocalJSON<{ step: number }>("draft");
    expect(value).toEqual({ step: 1 });
  });
});
