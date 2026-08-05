import React, { useState } from "react";
import { View, ScrollView, Pressable, Image } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";
import { useGlobalServicesQuery } from "../../api/globalServices/useGlobalServicesQuery";
import { GlobalService } from "../../domain/globalServices";
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
      <AppText variant="bodyStrong" style={{ marginBottom: theme.spacing.sm }}>More from Fuvay</AppText>
      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
        {services.map(service => (
          <Pressable
            key={service.id}
            onPress={() => setSelected(service)}
            accessibilityRole="button"
            accessibilityLabel={`${service.name}, request a callback`}
            style={{
              width: 160, marginRight: theme.spacing.sm, padding: theme.spacing.sm,
              borderRadius: theme.radiusUsage.card, backgroundColor: theme.colors.surfaceDefault,
              borderWidth: 1, borderColor: theme.colors.borderSubtle,
            }}
          >
            <View
              style={{
                width: 36, height: 36, borderRadius: theme.radiusUsage.input,
                backgroundColor: theme.colors.surfaceInteractive, alignItems: "center", justifyContent: "center",
                marginBottom: theme.spacing.sm, overflow: "hidden",
              }}
            >
              {service.iconUrl ? (
                <Image source={{ uri: service.iconUrl }} style={{ width: "100%", height: "100%" }} resizeMode="contain" />
              ) : (
                <Icon name="call-outline" size="standard" color={theme.colors.iconDefault} decorative />
              )}
            </View>
            <AppText variant="bodyStrong" numberOfLines={2}>{service.name}</AppText>
            {service.tagline ? (
              <AppText variant="caption" color="tertiary" numberOfLines={2} style={{ marginTop: theme.spacing.xxs }}>
                {service.tagline}
              </AppText>
            ) : null}
          </Pressable>
        ))}
      </ScrollView>
      <GlobalServiceInquiryModal
        service={selected}
        defaultName={defaultName}
        defaultZipcode={defaultZipcode}
        onClose={() => setSelected(null)}
      />
    </View>
  );
}
