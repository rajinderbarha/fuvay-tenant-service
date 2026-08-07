import React, { useState } from "react";
import { View, Pressable, Image } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";
import { useGlobalServicesQuery } from "../../api/globalServices/useGlobalServicesQuery";
import { GlobalService } from "../../domain/globalServices";
import { resolveGlobalServiceIcon } from "../../domain/globalServiceIcon";
import { resolveGlobalServiceAccent } from "../../domain/globalServiceAccent";
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
      {/* Full-width cards, each in its own brand colour, artwork on the
          right. Previously a 2-up grid of white cards; the updated design
          gives every offering its own identity colour and the extra width
          lets the description breathe instead of wrapping at ~150px.
          Colours are fixed brand accents rather than theme surfaces -- see
          domain/globalServiceAccent.ts for why they do not swap per theme. */}
      <View style={{ gap: theme.spacing.sm }}>
        {services.map(service => {
          const accent = resolveGlobalServiceAccent(service.name);
          return (
            <Pressable
              key={service.id}
              onPress={() => setSelected(service)}
              accessibilityRole="button"
              accessibilityLabel={`${service.name}, request a callback`}
              style={({ pressed }) => ({
                flexDirection: "row", alignItems: "center",
                borderRadius: theme.radiusUsage.card,
                backgroundColor: accent.background,
                paddingLeft: theme.spacing.base,
                paddingVertical: theme.spacing.base,
                overflow: "hidden",
                opacity: pressed ? 0.92 : 1,
              })}
            >
              <View style={{ flex: 1, minWidth: 0, paddingRight: theme.spacing.sm }}>
                <AppText variant="bodyStrong" numberOfLines={1} style={{ color: accent.onBackground }}>
                  {service.name}
                </AppText>
                {service.tagline ? (
                  <AppText
                    variant="caption"
                    numberOfLines={2}
                    style={{ color: accent.onBackgroundMuted, marginTop: 2 }}
                  >
                    {service.tagline}
                  </AppText>
                ) : null}
                <View
                  style={{
                    flexDirection: "row", alignItems: "center", gap: 4, alignSelf: "flex-start",
                    marginTop: theme.spacing.sm, paddingHorizontal: theme.spacing.sm, paddingVertical: 5,
                    borderRadius: theme.radiusUsage.statusPill,
                    // Translucent white rather than a theme colour: it has to
                    // sit legibly on six different card backgrounds.
                    backgroundColor: "rgba(255,255,255,0.18)",
                    borderWidth: 1, borderColor: "rgba(255,255,255,0.32)",
                  }}
                >
                  <AppText variant="labelStrong" style={{ color: accent.onBackground }}>Explore Service</AppText>
                  <Icon name="arrow-forward" size="compact" color={accent.onBackground} decorative />
                </View>
              </View>

              <View
                style={{
                  width: 92, height: 92, alignItems: "center", justifyContent: "center",
                  flexShrink: 0, marginRight: theme.spacing.sm,
                }}
              >
                {service.iconUrl ? (
                  <Image
                    source={{ uri: resolveMediaUrl(service.iconUrl)! }}
                    style={{ width: "100%", height: "100%" }}
                    resizeMode="contain"
                    accessibilityElementsHidden
                  />
                ) : (
                  // Was a hardcoded `call-outline` for every card, so the
                  // section was a column of identical phone icons. Admin
                  // artwork still wins; this only varies the fallback.
                  <Icon
                    name={resolveGlobalServiceIcon(service.name)}
                    size="navigation"
                    color={accent.onBackground}
                    decorative
                  />
                )}
              </View>
            </Pressable>
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
