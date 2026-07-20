import React, { useRef } from "react";
import { Pressable, type PressableProps, type AccessibilityRole } from "react-native";
import { useAppTheme } from "../../design-system/themes/use-app-theme";
import { duration } from "../../design-system/tokens/motion";

export interface AppPressableProps extends Omit<PressableProps, "accessibilityRole"> {
  accessibilityRole?: AccessibilityRole;
  accessibilityLabel?: string;
  accessibilityHint?: string;
  disabled?: boolean;
  testID?: string;
  hitSlop?: number;
  /** Enforced minimum touch target even if the visual content is smaller. */
  enforceMinTouchTarget?: boolean;
}

export function AppPressable({
  disabled,
  hitSlop = 0,
  enforceMinTouchTarget = true,
  style,
  children,
  accessibilityRole = "button",
  ...rest
}: AppPressableProps) {
  const { theme } = useAppTheme();
  const lastPressRef = useRef(0);
  const minSize = theme.sizes.touchTargetMin as number;

  const guardedOnPress: PressableProps["onPress"] = (event) => {
    // Double-tap protection: ignore presses within the "fast" motion window.
    const now = Date.now();
    if (now - lastPressRef.current < duration.fast) return;
    lastPressRef.current = now;
    rest.onPress?.(event);
  };

  return (
    <Pressable
      accessibilityRole={accessibilityRole}
      accessibilityState={{ disabled: Boolean(disabled) }}
      disabled={disabled}
      hitSlop={hitSlop}
      style={(state) => [
        enforceMinTouchTarget ? { minWidth: minSize, minHeight: minSize, alignItems: "center", justifyContent: "center" } : null,
        state.pressed ? { opacity: 0.7 } : null,
        typeof style === "function" ? style(state) : style,
      ]}
      {...rest}
      onPress={guardedOnPress}
    >
      {children}
    </Pressable>
  );
}
