import React from "react";
import { ExceptionalStateLayout } from "./ExceptionalStateLayout";

export interface MaintenanceScreenProps {
  onTryAgain: () => void;
  onGetHelp?: () => void;
}

/** Spec section 13 "Maintenance". */
export function MaintenanceScreen({ onTryAgain, onGetHelp }: MaintenanceScreenProps) {
  const actions = [{ label: "Try again", tone: "primary" as const, onPress: onTryAgain }];
  if (onGetHelp) actions.push({ label: "Get help", tone: "primary" as const, onPress: onGetHelp });
  return (
    <ExceptionalStateLayout
      icon="construct"
      title="Fuvay is temporarily unavailable"
      message="We're carrying out scheduled maintenance. Please check back shortly."
      actions={actions}
    />
  );
}
