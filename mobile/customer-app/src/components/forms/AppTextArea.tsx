import React from "react";
import { AppTextField, type AppTextFieldProps } from "./AppTextField";

export interface AppTextAreaProps extends Omit<AppTextFieldProps, "multiline"> {
  minHeight?: number;
  maxHeight?: number;
}

/** A multiline AppTextField with sensible min/max height defaults. */
export function AppTextArea({ minHeight = 88, maxHeight = 200, inputStyle, ...rest }: AppTextAreaProps) {
  return <AppTextField {...rest} multiline inputStyle={[{ minHeight, maxHeight }, inputStyle]} />;
}
