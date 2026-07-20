import AsyncStorage from "@react-native-async-storage/async-storage";
import { getActiveDraftId, setActiveDraftId, clearActiveDraftId } from "../draft-local-store";

beforeEach(async () => {
  await AsyncStorage.clear();
});

describe("draft local store", () => {
  it("starts with no active draft for a customer", async () => {
    expect(await getActiveDraftId("customer-a")).toBeNull();
  });

  it("stores and retrieves an active draft ID", async () => {
    await setActiveDraftId("customer-a", "draft-1");
    expect(await getActiveDraftId("customer-a")).toBe("draft-1");
  });

  it("clears the active draft ID", async () => {
    await setActiveDraftId("customer-a", "draft-1");
    await clearActiveDraftId("customer-a");
    expect(await getActiveDraftId("customer-a")).toBeNull();
  });

  it("isolates draft IDs between customers on the same device", async () => {
    await setActiveDraftId("customer-a", "draft-1");
    await setActiveDraftId("customer-b", "draft-2");
    expect(await getActiveDraftId("customer-a")).toBe("draft-1");
    expect(await getActiveDraftId("customer-b")).toBe("draft-2");
  });

  it("clearing one customer's draft never affects another customer's", async () => {
    await setActiveDraftId("customer-a", "draft-1");
    await setActiveDraftId("customer-b", "draft-2");
    await clearActiveDraftId("customer-a");
    expect(await getActiveDraftId("customer-a")).toBeNull();
    expect(await getActiveDraftId("customer-b")).toBe("draft-2");
  });
});
