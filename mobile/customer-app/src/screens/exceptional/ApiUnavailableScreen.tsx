import React from "react";
import { ExceptionalStateLayout } from "./ExceptionalStateLayout";

export interface ApiUnavailableScreenProps {
  onTryAgain: () => void;
  /** Only supplied by the caller when a genuinely safe cached experience
   * exists (spec section 13) -- Phase E never fabricates one itself. */
  onViewOfflineInformation?: () => void;
}

/** Spec section 13 "API unavailable". */
export function ApiUnavailableScreen({ onTryAgain, onViewOfflineInformation }: ApiUnavailableScreenProps) {
  const actions = [{ label: "Try again", tone: "primary" as const, onPress: onTryAgain }];
  if (onViewOfflineInformation) {
    actions.push({ label: "View offline information", tone: "primary" as const, onPress: onViewOfflineInformation });
  }
  return (
    <ExceptionalStateLayout
      icon="cloud-offline"
      title="We can't reach Fuvay right now"
      message="The service isn't responding at the moment. Please check your connection and try again."
      actions={actions}
    />
  );
}
