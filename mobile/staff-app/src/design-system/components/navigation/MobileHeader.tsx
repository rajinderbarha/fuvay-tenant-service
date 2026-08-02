import React from "react";
import { View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { IconButton } from "../actions/IconButton";

export interface MobileHeaderProps {
  title: string;
  onBack?: () => void;
  /** Single optional trailing action (e.g. notifications bell). Kept to
   * one slot deliberately -- this is a technician job-execution header,
   * not a tenant-admin toolbar. */
  actionIcon?: React.ComponentProps<typeof IconButton>["icon"];
  actionAccessibilityLabel?: string;
  onPressAction?: () => void;
}

/**
 * The one shared mobile header (spec section 11) used by every stack in
 * the app -- no screen renders its own bespoke header. Deliberately has no
 * workspace selector, global search, or tenant-admin controls: those
 * belong to the (separate, web-only) tenant portal, never this app.
 */
export function MobileHeader({ title, onBack, actionIcon, actionAccessibilityLabel, onPressAction }: MobileHeaderProps) {
  const { theme } = useTheme();
  const insets = useSafeAreaInsets();
  return (
    <View
      style={{
        paddingTop: insets.top,
        backgroundColor: theme.colors.backgroundPrimary,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.borderSubtle,
      }}
    >
      <View style={{ flexDirection: "row", alignItems: "center", height: 52, paddingHorizontal: theme.spacing.sm }}>
        <View style={{ width: 44 }}>
          {onBack ? <IconButton icon="chevron-back" accessibilityLabel="Back" onPress={onBack} /> : null}
        </View>
        <View style={{ flex: 1, alignItems: "center" }}>
          <AppText variant="bodyStrong" numberOfLines={1}>{title}</AppText>
        </View>
        <View style={{ width: 44, alignItems: "flex-end" }}>
          {actionIcon ? (
            <IconButton icon={actionIcon} accessibilityLabel={actionAccessibilityLabel ?? title} onPress={onPressAction ?? (() => {})} />
          ) : null}
        </View>
      </View>
    </View>
  );
}
