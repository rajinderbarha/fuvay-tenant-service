import React from "react";
import { ExceptionalStateLayout } from "./ExceptionalStateLayout";

export interface UpdateRequiredScreenProps {
  /** Store-URL resolution is not implemented this phase -- see Phase D
   * `appConfig.minSupportedVersion` = MISSING. `onUpdate` is a typed action
   * the caller can no-op or safely handle until real configuration
   * exists; this component never fabricates a store URL. */
  onUpdate: () => void;
}

/** Spec section 13 "Update required". */
export function UpdateRequiredScreen({ onUpdate }: UpdateRequiredScreenProps) {
  return (
    <ExceptionalStateLayout
      icon="arrow-up-circle"
      title="Update required"
      message="This version of the app is no longer supported. Please update to continue."
      actions={[{ label: "Update app", tone: "primary", onPress: onUpdate }]}
    />
  );
}
