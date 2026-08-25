import AsyncStorage from "@react-native-async-storage/async-storage";
import {
  clearServiceLocationPreference,
  loadServiceLocationPreference,
  normalizeServiceZipcode,
  saveServiceLocationPreference,
} from "../serviceLocationPreference";

describe("serviceLocationPreference", () => {
  beforeEach(async () => {
    await AsyncStorage.clear();
  });

  it("persists a normalized non-sensitive browsing PIN", async () => {
    await expect(saveServiceLocationPreference(" 140412 ")).resolves.toBe("140412");
    await expect(loadServiceLocationPreference()).resolves.toBe("140412");
  });

  it("rejects invalid values and ignores invalid stored data", async () => {
    expect(normalizeServiceZipcode("../../token")).toBeNull();
    await expect(saveServiceLocationPreference("../../token")).rejects.toThrow("Invalid service location");
    await AsyncStorage.setItem("customer_app_service_location_v1", "../../token");
    await expect(loadServiceLocationPreference()).resolves.toBeNull();
  });

  it("clears the selection without touching saved addresses", async () => {
    await saveServiceLocationPreference("140412");
    await clearServiceLocationPreference();
    await expect(loadServiceLocationPreference()).resolves.toBeNull();
  });
});
