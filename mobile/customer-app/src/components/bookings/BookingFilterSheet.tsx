import React from "react";
import { Modal, View, Pressable, ScrollView } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppButton } from "../AppButton";
import { AppIconButton } from "../AppIconButton";
import { Icon } from "../Icon";
import { BOOKING_STATUS_FILTERS } from "../../domain/bookingStatusFilter";

export interface BookingFilterSheetProps {
  visible: boolean;
  /** Currently applied raw status, or null for "Any status". */
  status: string | null;
  onClose: () => void;
  onApply: (status: string | null) => void;
}

/**
 * Status filter for My Bookings.
 *
 * Every option narrows on a real `ServiceBooking.status` the backend
 * already accepts (`status` query param), so a selection here always
 * produces a genuinely server-filtered list rather than a client-side
 * pass over the pages that happen to be loaded.
 *
 * Selection is committed on Apply, not on tap, so the list is not
 * refetched once per option while the customer is still deciding.
 */
export function BookingFilterSheet({ visible, status, onClose, onApply }: BookingFilterSheetProps) {
  const { theme } = useTheme();
  const [draft, setDraft] = React.useState<string | null>(status);

  React.useEffect(() => {
    if (visible) setDraft(status);
  }, [visible, status]);

  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <View style={{ flex: 1, justifyContent: "flex-end", backgroundColor: theme.colors.backgroundOverlay }}>
        <View
          style={{
            backgroundColor: theme.colors.surfaceDefault,
            borderTopLeftRadius: theme.radiusUsage.card,
            borderTopRightRadius: theme.radiusUsage.card,
            padding: theme.spacing.base,
            gap: theme.spacing.sm,
            maxHeight: "80%",
          }}
        >
          <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
            <AppText variant="headingSmall" accessibilityRole="header">Filter bookings</AppText>
            <AppIconButton name="close" accessibilityLabel="Close" onPress={onClose} />
          </View>

          <AppText variant="bodySmall" color="secondary">Status</AppText>

          <ScrollView>
            <View style={{ gap: theme.spacing.xxs }}>
              {BOOKING_STATUS_FILTERS.map(option => {
                const selected = draft === option.value;
                return (
                  <Pressable
                    key={option.label}
                    onPress={() => setDraft(option.value)}
                    accessibilityRole="radio"
                    accessibilityState={{ selected }}
                    accessibilityLabel={option.label}
                    style={{
                      flexDirection: "row", alignItems: "center", justifyContent: "space-between",
                      minHeight: theme.touchTargets.comfortable,
                      paddingHorizontal: theme.spacing.base,
                      borderRadius: theme.radiusUsage.input,
                      backgroundColor: selected ? theme.colors.surfaceInteractive : "transparent",
                    }}
                  >
                    <AppText variant="body">{option.label}</AppText>
                    {selected ? (
                      <Icon name="checkmark" size="standard" color={theme.colors.brandPrimaryStrong} decorative />
                    ) : null}
                  </Pressable>
                );
              })}
            </View>
          </ScrollView>

          <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
            <View style={{ flex: 1 }}>
              <AppButton label="Clear" tone="secondary" fullWidth onPress={() => { onApply(null); onClose(); }} />
            </View>
            <View style={{ flex: 1 }}>
              <AppButton label="Apply" fullWidth onPress={() => { onApply(draft); onClose(); }} />
            </View>
          </View>
        </View>
      </View>
    </Modal>
  );
}
