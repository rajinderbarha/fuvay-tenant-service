import React, { useMemo } from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { buildFuvayTheme } from "../../design-system/tokens/fuvay";
import { AppText } from "../AppText";

export type LoginMethod = "otp" | "password";

export interface LoginMethodSegmentedControlProps {
  value: LoginMethod;
  onChange: (method: LoginMethod) => void;
}

/**
 * Sign-in method tabs — Fuvay v2 underline treatment.
 *
 * v2 drops the bordered segmented pill for two text tabs over a rule, with
 * the active one carrying a 2px accent underline. The icons go with it: at
 * this size they competed with the labels for the eye without adding
 * meaning.
 *
 * Selection is still never conveyed by colour alone — the active tab is
 * semibold AND underlined AND reports `accessibilityState.selected`, so it
 * survives greyscale, low vision, and a screen reader (spec section 22,
 * "Segmented Login methods expose selected state").
 */
export function LoginMethodSegmentedControl({ value, onChange }: LoginMethodSegmentedControlProps) {
  const { theme, mode } = useTheme();
  const fuvay = useMemo(() => buildFuvayTheme(mode === "dark"), [mode]);
  const options: { key: LoginMethod; label: string }[] = [
    { key: "otp", label: "One-time code" },
    { key: "password", label: "Password" },
  ];

  return (
    <View>
      <View accessibilityRole="tablist" style={{ flexDirection: "row", gap: 22 }}>
        {options.map((opt) => {
          const selected = opt.key === value;
          return (
            <Pressable
              key={opt.key}
              onPress={() => onChange(opt.key)}
              accessibilityRole="tab"
              accessibilityState={{ selected }}
              // The tab label is small, so the row keeps a full-height touch
              // target rather than relying on the text's own bounds.
              style={{ minHeight: theme.touchTargets.minimum, justifyContent: "center", gap: 9 }}
            >
              <AppText
                variant={selected ? "bodyStrong" : "body"}
                style={{ color: selected ? theme.colors.textPrimary : theme.colors.textTertiary }}
              >
                {opt.label}
              </AppText>
              <View
                style={{
                  height: 2,
                  borderRadius: 2,
                  backgroundColor: selected ? fuvay.accents.a2 : "transparent",
                }}
              />
            </Pressable>
          );
        })}
      </View>
      <View style={{ height: 1, marginTop: -1, backgroundColor: theme.colors.divider }} />
    </View>
  );
}
