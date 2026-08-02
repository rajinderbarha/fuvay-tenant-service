import React from "react";
import { BaseButton, BaseButtonProps } from "./BaseButton";

type VariantProps = Omit<BaseButtonProps, "tone">;

export function PrimaryButton(props: VariantProps) {
  return <BaseButton tone="primary" {...props} />;
}
export function SecondaryButton(props: VariantProps) {
  return <BaseButton tone="secondary" {...props} />;
}
export function TertiaryButton(props: VariantProps) {
  return <BaseButton tone="tertiary" {...props} />;
}
export function DestructiveButton(props: VariantProps) {
  return <BaseButton tone="destructive" {...props} />;
}

/** AsyncButton -- explicit alias for a button whose onPress returns a
 * Promise. BaseButton already handles the busy/double-submit guard for any
 * async onPress; this alias exists so call sites can self-document intent. */
export const AsyncButton = PrimaryButton;
