import React from "react";
import { ExceptionalStateLayout } from "./ExceptionalStateLayout";

export interface ExceptionalScreenProps {
  reason: string;
  onGoToSignIn: () => void;
  onGetHelp: () => void;
}

/** Spec section 13 "Session expired". Does not implement real Login --
 * `onGoToSignIn` routes to the typed public LoginMethod screen -- once
 * Customer Login phase replaces it. */
export function SessionExpiredScreen({ onGoToSignIn, onGetHelp }: ExceptionalScreenProps) {
  return (
    <ExceptionalStateLayout
      tone="dark"
      icon="lock-closed"
      title="Session expired"
      message="Sign in again to continue securely."
      actions={[
        { label: "Go to sign in", tone: "primary", onPress: onGoToSignIn },
        { label: "Get help", tone: "secondary", onPress: onGetHelp },
      ]}
    />
  );
}
