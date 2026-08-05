import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppBadge } from "../AppBadge";
import { AppButton } from "../AppButton";
import { Icon } from "../Icon";
import { CustomerSavedAddress } from "../../domain/customerSavedAddress";
import { formatSavedAddress } from "../../domain/formatAddress";
import { maskPhoneForDisplay } from "../../domain/phone";

export interface SavedAddressCardProps {
  address: CustomerSavedAddress;
  canEdit: boolean;
  canDelete: boolean;
  onEdit?: () => void;
  onDelete?: () => void;
  onSetDefault?: () => void;
  settingDefault?: boolean;
}

/** Never fabricates a second recipient-name field (see adapter comment --
 * the real backend has one `name` column). Default status is shown via
 * both the badge AND the helper text below, never color alone (spec
 * section 12). */
export function SavedAddressCard({ address, canEdit, canDelete, onEdit, onDelete, onSetDefault, settingDefault }: SavedAddressCardProps) {
  const { theme } = useTheme();
  const label = address.label ?? "Address";

  return (
    <AppCard
      style={{ gap: theme.spacing.sm }}
      accessible
      accessibilityLabel={`${label}${address.isDefault ? ", default address" : ""}. ${formatSavedAddress(address)}`}
    >
      <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start" }}>
        <View style={{ width: 44, height: 44, borderRadius: theme.radiusUsage.card, backgroundColor: theme.colors.surfaceInteractive, alignItems: "center", justifyContent: "center" }}>
          <Icon name={address.isDefault ? "home-outline" : "location-outline"} size="standard" color={theme.colors.textSecondary} decorative />
        </View>
        <View style={{ flex: 1, gap: theme.spacing.xxs }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs }}>
            <AppText variant="bodyStrong">{label}</AppText>
            {address.isDefault ? <AppBadge label="Default" tone="success" /> : null}
          </View>
          {address.recipientName ? <AppText variant="body">{address.recipientName}</AppText> : null}
          <AppText variant="bodySmall" color="secondary">{formatSavedAddress(address)}</AppText>
          {address.mobile ? <AppText variant="bodySmall" color="secondary">{maskPhoneForDisplay(address.mobile)}</AppText> : null}
        </View>
      </View>

      {(canEdit && onEdit) || (canDelete && onDelete) ? (
        <View style={{ flexDirection: "row", gap: theme.spacing.sm, borderTopWidth: 1, borderTopColor: theme.colors.borderSubtle, paddingTop: theme.spacing.sm }}>
          {canEdit && onEdit ? (
            <AppButton
              label="Edit" tone="secondary" size="compact" onPress={onEdit}
              accessibilityLabel={`Edit ${label}`}
              leadingIcon={<Icon name="pencil-outline" size="compact" color={theme.colors.textPrimary} decorative />}
            />
          ) : null}
          {canDelete && onDelete ? (
            <AppButton label="Delete" tone="tertiary" size="compact" onPress={onDelete} accessibilityLabel={`Delete ${label}`} />
          ) : null}
        </View>
      ) : null}

      {address.isDefault ? (
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}>
          <Icon name="shield-checkmark" size="compact" color={theme.colors.statusSuccess} decorative />
          <AppText variant="caption" color="secondary">Used as the suggested address for new service requests.</AppText>
        </View>
      ) : onSetDefault ? (
        <AppText
          variant="labelStrong" color="link" onPress={onSetDefault}
          accessibilityRole="button" accessibilityLabel={`Set ${label} as default address`}
        >
          {settingDefault ? "Setting as default…" : "Set as default"}
        </AppText>
      ) : null}
    </AppCard>
  );
}
