import React from "react";
import { ErrorState } from "../States";

export function HomeErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <ErrorState
      title="We couldn't load your home screen"
      message="Please check your connection and try again."
      actionLabel="Try again"
      onAction={onRetry}
    />
  );
}
