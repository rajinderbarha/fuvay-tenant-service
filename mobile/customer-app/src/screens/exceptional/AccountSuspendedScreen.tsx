import React from "react";
import { ExceptionalStateLayout } from "./ExceptionalStateLayout";

export interface AccountSuspendedScreenProps {
  onContactSupport: () => void;
  onSignOut: () => void;
}

/** Spec section 13 "Account suspended". Deliberately generic wording --
 * never surfaces an internal suspension reason unless the backend
 * explicitly marks it customer-safe (no such field exists yet per the
 * Phase D capability registry, so this never varies by reason today). */
export function AccountSuspendedScreen({ onContactSupport, onSignOut }: AccountSuspendedScreenProps) {
  return (
    <ExceptionalStateLayout
      tone="dark"
      icon="alert-circle"
      title="Account restricted"
      message="Your account access is currently restricted. Contact support if you believe this is a mistake."
      actions={[
        { label: "Contact support", tone: "primary", onPress: onContactSupport },
        { label: "Sign out", tone: "secondary", onPress: onSignOut },
      ]}
    />
  );
}
