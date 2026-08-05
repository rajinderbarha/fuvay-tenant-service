import React from "react";
import { ExceptionalStateLayout } from "./ExceptionalStateLayout";

export interface VerticalUnavailableScreenProps {
  onBackToHome: () => void;
  onViewAvailableServices: () => void;
}

/** Spec section 13 "Vertical unavailable" -- used ONLY for a specific
 * selected vertical or deep link, never for the whole app (a disabled
 * Home Services vertical must not remove unrelated enabled verticals). */
export function VerticalUnavailableScreen({ onBackToHome, onViewAvailableServices }: VerticalUnavailableScreenProps) {
  return (
    <ExceptionalStateLayout
      icon="grid"
      title="This service isn't available yet"
      message="The service you're looking for isn't enabled in your area right now."
      actions={[
        { label: "Back to Home", tone: "primary", onPress: onBackToHome },
        { label: "View available services", tone: "secondary", onPress: onViewAvailableServices },
      ]}
    />
  );
}
