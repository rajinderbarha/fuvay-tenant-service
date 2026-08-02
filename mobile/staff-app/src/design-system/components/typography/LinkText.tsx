import React from "react";
import { Pressable } from "react-native";
import { AppText, AppTextProps } from "./AppText";

export interface LinkTextProps extends Omit<AppTextProps, "variant" | "color"> {
  onPress: () => void;
  disabled?: boolean;
}

/** LinkText -- inline pressable text link. Not a navigation component --
 * feature code supplies the onPress (which may push a route, open a sheet,
 * etc). Underline signals "link" without relying on color alone. */
export function LinkText({ onPress, disabled, style, children, ...rest }: LinkTextProps) {
  return (
    <Pressable onPress={onPress} disabled={disabled} accessibilityRole="link" accessibilityState={{ disabled }}>
      <AppText
        variant="body"
        color={disabled ? "disabled" : "link"}
        style={[{ textDecorationLine: "underline" }, style]}
        {...rest}
      >
        {children}
      </AppText>
    </Pressable>
  );
}
