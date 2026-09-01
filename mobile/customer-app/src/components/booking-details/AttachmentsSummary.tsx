import React, { useState } from "react";
import { View, Modal, Pressable, Image, ScrollView } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppIconButton } from "../AppIconButton";
import { Icon } from "../Icon";
import { CustomerAttachment } from "../../domain/customerBookingDetails";
import { resolveMediaImageSource } from "../../domain/mediaUrl";
import { getInMemoryAccessToken } from "../../api/session/tokenVault";

/**
 * "View details" opens a real sheet with the full photos and note --
 * there is no separate attachments SCREEN anywhere in this app, so rather
 * than link to one that doesn't exist (or omit the link, as this card
 * previously did), the detail is built as a modal using exactly the data
 * this card already has. Nothing here is fetched separately.
 */
export function AttachmentsSummary({ attachments, note }: { attachments: CustomerAttachment[]; note: string | null }) {
  const { theme } = useTheme();
  const [open, setOpen] = useState(false);
  const hasDetail = attachments.length > 0 || !!note;

  return (
    <AppCard>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <AppText variant="labelStrong" color="secondary">Attachments & notes</AppText>
        {hasDetail ? (
          <Pressable
            onPress={() => setOpen(true)}
            accessibilityRole="button"
            accessibilityLabel="View attachment and note details"
            style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}
          >
            <AppText variant="labelStrong" color="link">View details</AppText>
            <Icon name="chevron-forward" size="compact" color={theme.colors.brandPrimary} decorative />
          </Pressable>
        ) : null}
      </View>

      <View style={{ flexDirection: "row", gap: theme.spacing.base, marginTop: theme.spacing.sm }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs, flex: 1, minWidth: 0 }}>
          <View
            style={{
              width: 36, height: 36, borderRadius: theme.radius.radiusFull,
              backgroundColor: theme.colors.accentViolet, alignItems: "center", justifyContent: "center", flexShrink: 0,
            }}
          >
            <Icon name="image-outline" size="compact" color={theme.colors.textInverse} decorative />
          </View>
          <AppText variant="bodySmall" numberOfLines={1}>
            {attachments.length > 0 ? `${attachments.length} photo${attachments.length === 1 ? "" : "s"}` : "No photos"}
          </AppText>
        </View>
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs, flex: 1, minWidth: 0 }}>
          <View
            style={{
              width: 36, height: 36, borderRadius: theme.radius.radiusFull,
              backgroundColor: theme.colors.statusWarning, alignItems: "center", justifyContent: "center", flexShrink: 0,
            }}
          >
            <Icon name="document-text-outline" size="compact" color={theme.colors.textInverse} decorative />
          </View>
          <AppText variant="bodySmall" numberOfLines={1}>{note ?? "No additional note"}</AppText>
        </View>
      </View>

      <Modal visible={open} transparent animationType="slide" onRequestClose={() => setOpen(false)}>
        <View style={{ flex: 1, justifyContent: "flex-end", backgroundColor: theme.colors.backgroundOverlay }}>
          <View
            style={{
              backgroundColor: theme.colors.surfaceDefault,
              borderTopLeftRadius: theme.radiusUsage.card, borderTopRightRadius: theme.radiusUsage.card,
              padding: theme.spacing.base, gap: theme.spacing.base, maxHeight: "80%",
            }}
          >
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
              <AppText variant="headingSmall">Attachments & notes</AppText>
              <AppIconButton name="close" onPress={() => setOpen(false)} accessibilityLabel="Close" />
            </View>

            <ScrollView>
              {attachments.length > 0 ? (
                <View style={{ gap: theme.spacing.xs }}>
                  <AppText variant="labelStrong" color="secondary">
                    {attachments.length} photo{attachments.length === 1 ? "" : "s"}
                  </AppText>
                  <View style={{ flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.xs }}>
                    {attachments.map(a => {
                      const source = resolveMediaImageSource(a.url, getInMemoryAccessToken());
                      return source ? (
                        <Image
                          key={a.id}
                          source={source}
                          style={{ width: 96, height: 96, borderRadius: theme.radiusUsage.input, backgroundColor: theme.colors.surfaceSecondary }}
                          resizeMode="cover"
                          accessibilityLabel="Booking photo"
                        />
                      ) : null;
                    })}
                  </View>
                </View>
              ) : (
                <AppText variant="bodySmall" color="tertiary">No photos were attached.</AppText>
              )}

              <View style={{ marginTop: theme.spacing.base, gap: theme.spacing.xs }}>
                <AppText variant="labelStrong" color="secondary">Additional note</AppText>
                <AppText variant="body">{note ?? "No additional note was added."}</AppText>
              </View>
            </ScrollView>
          </View>
        </View>
      </Modal>
    </AppCard>
  );
}
