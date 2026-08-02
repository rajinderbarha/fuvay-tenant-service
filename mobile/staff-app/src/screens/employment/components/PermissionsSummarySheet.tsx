import React from "react";
import { View, ScrollView } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { BottomSheet } from "../../../design-system/components/overlays/BottomSheet";
import { Heading } from "../../../design-system/components/typography/Heading";
import { AppText } from "../../../design-system/components/typography/AppText";
import { Icon } from "../../../design-system/components/Icon";
import { PermissionsSummaryDTO } from "../../../services/employment/types";

/** Human-readable, read-only Permissions Summary (spec section 9). Every
 * item is derived server-side from the real "technician" role permission
 * list -- never raw permission codes as the primary UI. */
export function PermissionsSummarySheet({ visible, onClose, permissions }: {
  visible: boolean; onClose: () => void; permissions: PermissionsSummaryDTO | null;
}) {
  const { theme } = useTheme();
  return (
    <BottomSheet visible={visible} onClose={onClose}>
      <ScrollView contentContainerStyle={{ paddingBottom: theme.spacing.xl }}>
        <Heading level="medium">Your permissions</Heading>
        <AppText variant="bodySmall" color="tertiary" style={{ marginTop: theme.spacing.xs, marginBottom: theme.spacing.base }}>
          {permissions ? `${permissions.capability_count} capabilities enabled` : "Permissions unavailable"}
        </AppText>
        {permissions?.groups.map(group => (
          <View key={group.key} style={{ marginBottom: theme.spacing.base }}>
            <AppText variant="bodyStrong" style={{ marginBottom: theme.spacing.xs }}>{group.label}</AppText>
            {group.items.length === 0 ? (
              <AppText variant="bodySmall" color="tertiary">None</AppText>
            ) : group.items.map(item => (
              <View key={item} style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs, marginBottom: 4 }}>
                <Icon
                  name={group.key === "restricted" ? "close-circle-outline" : "checkmark-circle-outline"}
                  size="compact"
                  color={group.key === "restricted" ? theme.colors.textTertiary : theme.colors.statusSuccess}
                  decorative
                />
                <AppText variant="bodySmall" color={group.key === "restricted" ? "tertiary" : "primary"}>{item}</AppText>
              </View>
            ))}
          </View>
        ))}
      </ScrollView>
    </BottomSheet>
  );
}
