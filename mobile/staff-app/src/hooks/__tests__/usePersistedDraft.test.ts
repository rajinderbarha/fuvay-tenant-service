import { renderHook, act, waitFor } from "@testing-library/react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { usePersistedDraft } from "../usePersistedDraft";

describe("usePersistedDraft", () => {
  beforeEach(async () => {
    await AsyncStorage.clear();
  });

  it("starts with the initial value when nothing is persisted", async () => {
    const { result } = renderHook(() => usePersistedDraft("test_key_1", { text: "" }));
    await waitFor(() => expect(result.current.loaded).toBe(true));
    expect(result.current.draft).toEqual({ text: "" });
    expect(result.current.hasPersistedDraft).toBe(false);
  });

  it("persists a draft to AsyncStorage and survives a fresh hook instance (simulates app restart)", async () => {
    const { result, unmount } = renderHook(() => usePersistedDraft("test_key_2", { text: "" }));
    await waitFor(() => expect(result.current.loaded).toBe(true));

    act(() => { result.current.setDraft({ text: "in progress notes" }); });
    await waitFor(() => expect(result.current.hasPersistedDraft).toBe(true));
    unmount();

    // Fresh hook instance, same key -- simulates a real app restart reading
    // the same AsyncStorage-backed draft back.
    const { result: result2 } = renderHook(() => usePersistedDraft("test_key_2", { text: "" }));
    await waitFor(() => expect(result2.current.loaded).toBe(true));
    expect(result2.current.draft).toEqual({ text: "in progress notes" });
    expect(result2.current.hasPersistedDraft).toBe(true);
  });

  it("clearDraft resets to the initial value and removes the persisted entry", async () => {
    const { result } = renderHook(() => usePersistedDraft("test_key_3", { text: "" }));
    await waitFor(() => expect(result.current.loaded).toBe(true));

    act(() => { result.current.setDraft({ text: "draft content" }); });
    await waitFor(() => expect(result.current.hasPersistedDraft).toBe(true));

    act(() => { result.current.clearDraft(); });
    expect(result.current.draft).toEqual({ text: "" });
    expect(result.current.hasPersistedDraft).toBe(false);

    const stored = await AsyncStorage.getItem("serviceos_staff_draft_test_key_3");
    expect(stored).toBeNull();
  });

  it("keeps different keys' drafts fully independent", async () => {
    const { result: a } = renderHook(() => usePersistedDraft("test_key_a", { v: 1 }));
    const { result: b } = renderHook(() => usePersistedDraft("test_key_b", { v: 1 }));
    await waitFor(() => expect(a.current.loaded).toBe(true));
    await waitFor(() => expect(b.current.loaded).toBe(true));

    act(() => { a.current.setDraft({ v: 99 }); });
    await waitFor(() => expect(a.current.hasPersistedDraft).toBe(true));

    expect(a.current.draft).toEqual({ v: 99 });
    expect(b.current.draft).toEqual({ v: 1 });
  });
});
