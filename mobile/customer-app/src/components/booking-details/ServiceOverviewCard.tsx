import React, { useState } from "react";
import { View, Modal, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppIconButton } from "../AppIconButton";
import { CustomerBookingDetails } from "../../domain/customerBookingDetails";

/** Renders whatever answers the finalized booking actually carries --
 * never a hardcoded AC-only field list (spec section 5: "The screen must
 * support categories with different questions"). `View all answers`
 * opens a read-only sheet; there is no path back into the editable
 * assistant flow from here. */
export function ServiceOverviewCard({ service }: { service: CustomerBookingDetails["service"] }) {
  const { theme } = useTheme();
  const [open, setOpen] = useState(false);
  const preview = service.answers.slice(0, 4);

  return (
    <AppCard>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" }}>
        <View style={{ flex: 1 }}>
          <AppText variant="labelStrong" color="secondary">Service overview</AppText>
          {service.name ? <AppText variant="bodyStrong" style={{ marginTop: theme.spacing.xxs }}>{service.name}</AppText> : null}
          {service.inspectionRequired ? <AppText variant="bodySmall" color="secondary">Inspection-based service</AppText> : null}
        </View>
        {service.answers.length > 0 ? (
          <AppText variant="labelStrong" color="link" onPress={() => setOpen(true)}>View all answers</AppText>
        ) : null}
      </View>

      {service.issueSummary ? <AppText variant="body" style={{ marginTop: theme.spacing.xs }}>Issue: {service.issueSummary}</AppText> : null}
      {preview.map(a => <AppText key={a.id} variant="body">{a.label}: {a.value}</AppText>)}

      <Modal visible={open} transparent animationType="slide" onRequestClose={() => setOpen(false)}>
        <View style={{ flex: 1, justifyContent: "flex-end", backgroundColor: theme.colors.backgroundOverlay }}>
          <View style={{ backgroundColor: theme.colors.surfaceDefault, borderTopLeftRadius: theme.radiusUsage.card, borderTopRightRadius: theme.radiusUsage.card, padding: theme.spacing.base, gap: theme.spacing.xs }}>
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
              <AppText variant="headingSmall">All answers</AppText>
              <AppIconButton name="close" onPress={() => setOpen(false)} accessibilityLabel="Close" />
            </View>
            {service.answers.map(a => (
              <View key={a.id} style={{ flexDirection: "row", justifyContent: "space-between", paddingVertical: theme.spacing.xxs }}>
                <AppText variant="body" color="secondary">{a.label}</AppText>
                <AppText variant="body">{a.value}</AppText>
              </View>
            ))}
          </View>
        </View>
      </Modal>
    </AppCard>
  );
}
