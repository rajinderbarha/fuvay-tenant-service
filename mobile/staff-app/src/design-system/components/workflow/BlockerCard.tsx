import React from "react";
import { BlockingBanner } from "../feedback/Banner";
import { BlockerPresentationModel } from "../../types";

/** Thin typed wrapper over BlockingBanner for a workflow BlockerPresentationModel. */
export function BlockerCard({ blocker }: { blocker: BlockerPresentationModel }) {
  return (
    <BlockingBanner
      title={blocker.title}
      message={blocker.message}
      blockCode={blocker.code}
      permittedNextActionLabel={blocker.permittedNextActionLabel}
      severity={blocker.severity}
    />
  );
}
