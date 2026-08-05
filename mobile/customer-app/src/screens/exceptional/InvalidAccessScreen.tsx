import React from "react";
import { ExceptionalStateLayout } from "./ExceptionalStateLayout";

export interface InvalidAccessScreenProps {
  onSignOut: () => void;
}

/** Spec section 13 "Invalid customer access" -- reached whenever a
 * non-customer token (staff/technician/tenant-owner/admin), a missing
 * customer audience, or corrupted session metadata is detected. Never
 * shows authenticated customer tabs underneath this. */
export function InvalidAccessScreen({ onSignOut }: InvalidAccessScreenProps) {
  return (
    <ExceptionalStateLayout
      tone="dark"
      icon="close-circle"
      title="This account can't access the customer app"
      message="The signed-in account isn't a customer account. Please sign out and use a customer account."
      actions={[{ label: "Sign out", tone: "primary", onPress: onSignOut }]}
    />
  );
}
