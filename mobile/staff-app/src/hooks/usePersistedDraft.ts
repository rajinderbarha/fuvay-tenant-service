import { useCallback, useEffect, useRef, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";

/**
 * UX-05 Round 5: generic draft-persistence hook backed by AsyncStorage
 * (already a real dependency -- used by AuthContext/ThemeContext). Closes
 * the "draft persistence remains unimplemented" gap flagged in every prior
 * round's known-limitations.md for Inspection/Checklist/Notes drafts.
 *
 * Deliberately SIMPLE and explicit about its offline-safety boundary: this
 * persists a draft to local device storage only (survives app restart) --
 * it does NOT sync to any backend, does NOT resolve conflicts, and does NOT
 * auto-submit anything. Per the offline-operation-matrix.csv hard rule,
 * status transitions / submissions remain online_required and are never
 * triggered by this hook. `clearDraft()` must be called explicitly by the
 * consuming screen once a draft is successfully submitted for real (no
 * consuming screen in this round has a real submit endpoint yet, so
 * `clearDraft` is exercised by the "discard draft" path only).
 */
export function usePersistedDraft<T>(key: string, initial: T) {
  const storageKey = `serviceos_staff_draft_${key}`;
  const [draft, setDraftState] = useState<T>(initial);
  const [loaded, setLoaded] = useState(false);
  const [hasPersistedDraft, setHasPersistedDraft] = useState(false);
  const initialRef = useRef(initial);

  useEffect(() => {
    let cancelled = false;
    AsyncStorage.getItem(storageKey).then(raw => {
      if (cancelled) return;
      if (raw) {
        try {
          setDraftState(JSON.parse(raw) as T);
          setHasPersistedDraft(true);
        } catch { /* corrupt draft -- fall back to initial, don't crash */ }
      }
      setLoaded(true);
    }).catch(() => setLoaded(true));
    return () => { cancelled = true; };
  }, [storageKey]);

  const setDraft = useCallback((next: T | ((prev: T) => T)) => {
    setDraftState(prev => {
      const resolved = typeof next === "function" ? (next as (prev: T) => T)(prev) : next;
      AsyncStorage.setItem(storageKey, JSON.stringify(resolved)).catch(() => { /* non-fatal -- draft just won't persist this write */ });
      setHasPersistedDraft(true);
      return resolved;
    });
  }, [storageKey]);

  const clearDraft = useCallback(() => {
    setDraftState(initialRef.current);
    setHasPersistedDraft(false);
    AsyncStorage.removeItem(storageKey).catch(() => { /* non-fatal */ });
  }, [storageKey]);

  return { draft, setDraft, clearDraft, loaded, hasPersistedDraft };
}
