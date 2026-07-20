import AsyncStorage from "@react-native-async-storage/async-storage";
import { preferenceStorage } from "../preference-storage";
import { PREFERENCE_STORAGE_KEYS } from "../storage-keys";

describe("preferenceStorage", () => {
  beforeEach(async () => {
    await AsyncStorage.clear();
  });

  it("saves and reads back a value", async () => {
    await preferenceStorage.setItem(PREFERENCE_STORAGE_KEYS.themePreference, "dark");
    const value = await preferenceStorage.getItem(PREFERENCE_STORAGE_KEYS.themePreference);
    expect(value).toBe("dark");
  });

  it("returns null for an unset key", async () => {
    const value = await preferenceStorage.getItem(PREFERENCE_STORAGE_KEYS.localePreference);
    expect(value).toBeNull();
  });

  it("removes a value", async () => {
    await preferenceStorage.setItem(PREFERENCE_STORAGE_KEYS.onboardingComplete, true);
    await preferenceStorage.removeItem(PREFERENCE_STORAGE_KEYS.onboardingComplete);
    expect(await preferenceStorage.getItem(PREFERENCE_STORAGE_KEYS.onboardingComplete)).toBeNull();
  });

  it("recovers safely from a corrupted (non-JSON) stored value", async () => {
    await AsyncStorage.setItem(PREFERENCE_STORAGE_KEYS.themePreference, "{not-json");
    const value = await preferenceStorage.getItem(PREFERENCE_STORAGE_KEYS.themePreference);
    expect(value).toBeNull();
  });

  it("clearAll only removes preference-owned keys", async () => {
    await preferenceStorage.setItem(PREFERENCE_STORAGE_KEYS.themePreference, "light");
    await AsyncStorage.setItem("unrelated-app-key", "keep-me");
    await preferenceStorage.clearAll();
    expect(await preferenceStorage.getItem(PREFERENCE_STORAGE_KEYS.themePreference)).toBeNull();
    expect(await AsyncStorage.getItem("unrelated-app-key")).toBe("keep-me");
  });

  it("returns false instead of throwing when the underlying adapter fails", async () => {
    const spy = jest.spyOn(AsyncStorage, "setItem").mockRejectedValueOnce(new Error("disk full"));
    const ok = await preferenceStorage.setItem(PREFERENCE_STORAGE_KEYS.themePreference, "dark");
    expect(ok).toBe(false);
    spy.mockRestore();
  });
});
