import React from "react";
import { EmptyState } from "../States";

export function UnserviceableState({ zipcode, onChangeLocation }: { zipcode: string; onChangeLocation: () => void }) {
  return (
    <EmptyState
      icon="alert-circle-outline"
      title="Not available in your area yet"
      message={`We don't currently service ${zipcode}. Try a different location.`}
      actionLabel="Change location"
      onAction={onChangeLocation}
    />
  );
}
