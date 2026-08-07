import React, { useState } from "react";
import { View, Pressable, Image } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";
import { useGlobalServicesQuery } from "../../api/globalServices/useGlobalServicesQuery";
import { GlobalService } from "../../domain/globalServices";
import { resolveGlobalServiceIcon } from "../../domain/globalServiceIcon";
import { resolveMediaUrl } from "../../domain/mediaUrl";
import { GlobalServiceInquiryModal } from "./GlobalServiceInquiryModal";

export interface GlobalServicesSectionProps {
  /** Pre-fills the inquiry form; both optional since this section renders
   * even before an address/profile is known (fixed, shown on every
   * zipcode -- see HomeScreen, which mounts this in all three render
   * branches: ready, NoAddressState, UnserviceableState). */
  defaultName?: string;
  defaultZipcode?: string | null;
}

/**
 * Fixed, always-shown promotional section -- deliberately NOT driven by
 * the Home aggregation/serviceability query. GET /v1/customer/global-
 * services returns the same active list to every customer regardless of
 * ZIP or vertical (app/engines/global_services). Tapping a card opens an
 * inquiry form; submitting creates a Lead an admin calls back about --
 * there is no booking, provider match, or price anywhere in this flow.
 */
export function GlobalServicesSection({ defaultName, defaultZipcode }: GlobalServicesSectionProps) {
  const { theme } = useTheme();
  const query = useGlobalServicesQuery();
  const [selected, setSelected] = useState<GlobalService | null>(null);

  const services = query.data ?? [];
  if (query.isPending || query.isError || services.length === 0) return null;

  return (
    <View>
      {/* Title + inline qualifier, matching the other section headers. */}
      <View style={{ flexDirection: "row", alignItems: "baseline", gap: theme.spacing.xs, marginBottom: theme.spacing.sm }}>
        <AppText variant="headingSmall">Build with Fuvay</AppText>
        <AppText variant="caption" color="tertiary" numberOfLines={1}>Global services available</AppText>
      </View>
      {/* 2-up grid rather than a horizontal rail: these cards carry a
          description and their own CTA, so a 160px-wide scroller truncated
          both and hid everything past the second card. Explicit rows keep a
          trailing odd card the same width as the rest. */}
      <View style={{ gap: theme.spacing.sm }}>
        {Array.from({ length: Math.ceil(services.length / 2) }).map((_, rowIndex) => {
          const row = services.slice(rowIndex * 2, rowIndex * 2 + 2);
          return (
            <View key={rowIndex} style={{ flexDirection: "row", gap: theme.spacing.sm }}>
              {row.map(service => (
                <Pressable
                  key={service.id}
                  onPress={() => setSelected(service)}
                  accessibilityRole="button"
                  accessibilityLabel={`${service.name}, request a callback`}
                  style={({ pressed }) => ({
                    flex: 1, padding: theme.spacing.base,
                    borderRadius: theme.radiusUsage.card, backgroundColor: theme.colors.surfaceDefault,
                    borderWidth: 1,
                    borderColor: pressed ? theme.colors.brandPrimary : theme.colors.borderSubtle,
                    opacity: pressed ? 0.9 : 1,
                  })}
                >
                  <View
                    style={{
                      width: 40, height: 40, borderRadius: theme.radius.radiusFull,
                      alignItems: "center", justifyContent: "center",
                      marginBottom: theme.spacing.sm, overflow: "hidden",
                      // The supplied artwork is a full-bleed coloured disc, so
                      // it needs no tinted plate behind it; the glyph fallback
                      // does, otherwise it floats on the bare card.
                      backgroundColor: service.iconUrl ? "transparent" : theme.colors.brandPrimaryMuted,
                    }}
                  >
                    {service.iconUrl ? (
                      <Image source={{ uri: resolveMediaUrl(service.iconUrl)! }} style={{ width: "100%", height: "100%" }} resizeMode="contain" />
                    ) : (
                      // Was a hardcoded `call-outline` for every card, so a row of
                      // global services was a row of identical grey phone icons.
                      // Admin-uploaded iconUrl still wins; this only varies the
                      // fallback.
                      <Icon
                        name={resolveGlobalServiceIcon(service.name)}
                        size="standard"
                        color={theme.colors.brandPrimaryStrong}
                        decorative
                      />
                    )}
                  </View>
                  <AppText variant="bodyStrong" numberOfLines={2}>{service.name}</AppText>
                  {service.tagline ? (
                    <AppText variant="caption" color="tertiary" numberOfLines={2} style={{ marginTop: theme.spacing.xxs }}>
                      {service.tagline}
                    </AppText>
                  ) : null}
                  <View
                    style={{
                      flexDirection: "row", alignItems: "center", gap: 4, alignSelf: "flex-start",
                      marginTop: theme.spacing.sm, paddingHorizontal: theme.spacing.sm, paddingVertical: 5,
                      borderRadius: theme.radiusUsage.statusPill, backgroundColor: theme.colors.brandPrimary,
                    }}
                  >
                    <AppText variant="labelStrong" style={{ color: theme.colors.brandOnPrimary }}>Explore Service</AppText>
                    <Icon name="arrow-forward" size="compact" color={theme.colors.brandOnPrimary} decorative />
                  </View>
                </Pressable>
              ))}
              {row.length === 1 ? <View style={{ flex: 1 }} /> : null}
            </View>
          );
        })}
      </View>
      <GlobalServiceInquiryModal
        service={selected}
        defaultName={defaultName}
        defaultZipcode={defaultZipcode}
        onClose={() => setSelected(null)}
      />
    </View>
  );
}
