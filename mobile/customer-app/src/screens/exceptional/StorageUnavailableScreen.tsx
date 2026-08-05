import React from "react";
import { ExceptionalStateLayout } from "./ExceptionalStateLayout";

export interface StorageUnavailableScreenProps {
  onTryAgain: () => void;
}

/** Spec section 13 "Storage unavailable". Deliberately offers only a
 * retry -- no action here may encourage continuing without secure local
 * storage (that would risk session material never persisting safely). */
export function StorageUnavailableScreen({ onTryAgain }: StorageUnavailableScreenProps) {
  return (
    <ExceptionalStateLayout
      icon="shield-half"
      title="Secure storage unavailable"
      message="Fuvay couldn't access secure storage on this device. Please try again."
      actions={[{ label: "Try again", tone: "primary", onPress: onTryAgain }]}
    />
  );
}
