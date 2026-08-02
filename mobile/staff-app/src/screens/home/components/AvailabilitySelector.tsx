import React, { useState } from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { AppText } from "../../../design-system/components/typography/AppText";
import { Icon } from "../../../design-system/components/Icon";
import { ActionSheet } from "../../../design-system/components/overlays/ActionSheet";
import { AvailabilityState } from "../../../services/home/types";

const LABEL: Record<AvailabilityState, string> = { available: "Available", busy: "Busy", offline: "Offline" };

function toneColor(theme: ReturnType<typeof useTheme>["theme"], state: AvailabilityState) {
  if (state === "available") return theme.colors.statusSuccess;
  if (state === "busy") return theme.colors.statusWarning;
  return theme.colors.textTertiary;
}

export interface AvailabilitySelectorProps {
  state: AvailabilityState;
  disabled?: boolean;
  onChange: (state: AvailabilityState) => void;
}

/** The Home header's availability pill (spec section 2/8) -- backend-
 * authoritative, never a local-only toggle; the caller (TechnicianHomeScreen)
 * owns the optimistic-update + rollback via useTechnicianHome. */
export function AvailabilitySelector({ state, disabled, onChange }: AvailabilitySelectorProps) {
  const { theme } = useTheme();
  const [open, setOpen] = useState(false);
  const color = toneColor(theme, state);

  return (
    <>
      <Pressable
        onPress={() => !disabled && setOpen(true)}
        disabled={disabled}
        accessibilityRole="button"
        accessibilityLabel={`Availability: ${LABEL[state]}`}
        accessibilityHint="Double tap to change your availability"
        style={{
          flexDirection: "row", alignItems: "center", gap: 6, minHeight: 44,
          paddingHorizontal: theme.spacing.sm, borderRadius: theme.radiusUsage.button,
          borderWidth: 1, borderColor: theme.colors.borderDefault, backgroundColor: theme.colors.surfaceDefault,
          opacity: disabled ? theme.opacity.disabled : 1,
        }}
      >
        <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: color }} />
        <AppText variant="bodyStrong">{LABEL[state]}</AppText>
        <Icon name="chevron-down" size="compact" color={theme.colors.textTertiary} decorative />
      </Pressable>
      <ActionSheet
        visible={open}
        title="Set availability"
        options={(["available", "busy", "offline"] as AvailabilityState[]).map(s => ({ key: s, label: LABEL[s] }))}
        onSelect={key => { setOpen(false); onChange(key as AvailabilityState); }}
        onClose={() => setOpen(false)}
      />
    </>
  );
}
