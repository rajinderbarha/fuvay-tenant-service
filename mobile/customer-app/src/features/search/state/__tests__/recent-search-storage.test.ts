import AsyncStorage from "@react-native-async-storage/async-storage";
import { getRecentSearches, addRecentSearch, removeRecentSearch, clearRecentSearches } from "../recent-search-storage";

beforeEach(async () => {
  await AsyncStorage.clear();
});

describe("recent search storage", () => {
  it("starts empty for a customer with no history", async () => {
    expect(await getRecentSearches("customer-a")).toEqual([]);
  });

  it("adds a search term to the front of the list", async () => {
    await addRecentSearch("customer-a", "ac repair");
    const items = await addRecentSearch("customer-a", "plumbing");
    expect(items).toEqual(["plumbing", "ac repair"]);
  });

  it("moves a re-searched term to the front instead of duplicating it", async () => {
    await addRecentSearch("customer-a", "ac repair");
    await addRecentSearch("customer-a", "plumbing");
    const items = await addRecentSearch("customer-a", "ac repair");
    expect(items).toEqual(["ac repair", "plumbing"]);
  });

  it("caps the list at 10 entries", async () => {
    for (let i = 0; i < 15; i++) {
      await addRecentSearch("customer-a", `query-${i}`);
    }
    const items = await getRecentSearches("customer-a");
    expect(items).toHaveLength(10);
    expect(items[0]).toBe("query-14");
  });

  it("removes a single entry", async () => {
    await addRecentSearch("customer-a", "ac repair");
    await addRecentSearch("customer-a", "plumbing");
    const items = await removeRecentSearch("customer-a", "ac repair");
    expect(items).toEqual(["plumbing"]);
  });

  it("clears all entries for a customer", async () => {
    await addRecentSearch("customer-a", "ac repair");
    await clearRecentSearches("customer-a");
    expect(await getRecentSearches("customer-a")).toEqual([]);
  });

  it("isolates history between customers on the same device", async () => {
    await addRecentSearch("customer-a", "ac repair");
    await addRecentSearch("customer-b", "plumbing");
    expect(await getRecentSearches("customer-a")).toEqual(["ac repair"]);
    expect(await getRecentSearches("customer-b")).toEqual(["plumbing"]);
  });

  it("clearing one customer's history never affects another customer's", async () => {
    await addRecentSearch("customer-a", "ac repair");
    await addRecentSearch("customer-b", "plumbing");
    await clearRecentSearches("customer-a");
    expect(await getRecentSearches("customer-a")).toEqual([]);
    expect(await getRecentSearches("customer-b")).toEqual(["plumbing"]);
  });
});
