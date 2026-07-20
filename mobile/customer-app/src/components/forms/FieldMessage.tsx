import React from "react";
import { AppText } from "../primitives/AppText";

export type FieldMessageTone = "helper" | "error" | "success" | "warning";

export interface FieldMessageProps {
  tone?: FieldMessageTone;
  children: React.ReactNode;
}

const COLOR_BY_TONE = {
  helper: "textTertiary",
  error: "textDanger",
  success: "textSuccess",
  warning: "textWarning",
} as const;

export function FieldMessage({ tone = "helper", children }: FieldMessageProps) {
  return (
    <AppText variant="caption" color={COLOR_BY_TONE[tone]} accessibilityLiveRegion={tone === "error" ? "polite" : "none"}>
      {children}
    </AppText>
  );
}
