import React from "react";
import { EmptyState } from "../States";

export function NoAddressState({ onAddAddress }: { onAddAddress: () => void }) {
  return (
    <EmptyState
      icon="location-outline"
      title="Choose your location"
      message="Add an address so we can show services available near you."
      actionLabel="Choose your location"
      onAction={onAddAddress}
    />
  );
}
