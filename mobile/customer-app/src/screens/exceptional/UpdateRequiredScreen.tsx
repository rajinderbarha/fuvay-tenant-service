import React from "react";
import { ExceptionalStateLayout } from "./ExceptionalStateLayout";

export interface UpdateRequiredScreenProps {
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
