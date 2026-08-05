import React, { createContext, useContext, useMemo, useState } from "react";
import { SupportRequestDraft, createEmptySupportRequestDraft } from "../../domain/supportRequestDraft";

interface SupportRequestWizardValue {
  draft: SupportRequestDraft;
  setDraft: React.Dispatch<React.SetStateAction<SupportRequestDraft>>;
  resetDraft: () => void;
}

const SupportRequestWizardContext = createContext<SupportRequestWizardValue | null>(null);

/**
 * Scoped, in-memory-only draft state for the 3-step Create Support
 * Request wizard (spec section 2) -- lives only for the lifetime of the
 * nested wizard navigator, never written to AsyncStorage/secure storage,
 * and is the single source of truth Step 1/2/(3) all read and write
 * instead of passing the whole draft through navigation params.
 */
export function SupportRequestWizardProvider({ children }: { children: React.ReactNode }) {
  const [draft, setDraft] = useState<SupportRequestDraft>(createEmptySupportRequestDraft());
  const value = useMemo<SupportRequestWizardValue>(() => ({
    draft, setDraft, resetDraft: () => setDraft(createEmptySupportRequestDraft()),
  }), [draft]);
  return <SupportRequestWizardContext.Provider value={value}>{children}</SupportRequestWizardContext.Provider>;
}

export function useSupportRequestWizard(): SupportRequestWizardValue {
  const ctx = useContext(SupportRequestWizardContext);
  if (!ctx) {
    throw new Error("useSupportRequestWizard must be used within SupportRequestWizardProvider");
  }
  return ctx;
}
