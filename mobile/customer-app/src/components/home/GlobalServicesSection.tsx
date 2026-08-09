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
  /** Pre-fills the inquiry form; both optional since this section renders even
   * before an address/profile is known (it is fixed and shown on every zipcode
   * -- see HomeScreen, which mounts it in all three render branches). */
  defaultName?: string;
  defaultZipcode?: string | null;
  /** Admin heading override from the Home section settings. */
  title?: string | null;
}

/**
 * Project work you can ask Fuvay to quote: web, app, software.
 *
 * Fixed and always shown -- deliberately NOT driven by the Home aggregation or
 * serviceability query, because GET /v1/customer/global-services returns the
 * same active list to every customer regardless of ZIP. Tapping one opens an
 * inquiry form; submitting creates a Lead an admin calls back about. There is no
 * booking, no provider match and no price anywhere in this flow.
 *
 * REBUILT (this pass). It was a full-width paged carousel of saturated colour
 * cards, and it read as an advertisement someone had dropped into the middle of
 * a service app: each page filled the screen, only one was visible at a time, so
 * a customer had to swipe blind to learn a second offering even existed, and the
 * dots implied content they had no reason to expect.
 *
 * Now: one compact 2-up grid, everything visible at once, with each offering's
 * accent used as a TINT rather than a full bleed -- the identity colour survives
 * without the section shouting over the services above it. The subtitle states
 * plainly that this is a callback rather than a booking, which is the one thing a
 * customer most needs to know before tapping and the old design never said.
 */
export function GlobalServicesSection({ defaultName, defaultZipcode, title }: GlobalServicesSectionProps) {
  const { theme } = useTheme();
  const query = useGlobalServicesQuery();
  const [selected, setSelected] = useState<GlobalService | null>(null);

  const services = query.data ?? [];
  if (query.isPending || query.isError || services.length === 0) return null;

  const rows: GlobalService[][] = [];
  for (let i = 0; i < services.length; i += 2) rows.push(services.slice(i, i + 2));

  return (
    <View>
      <View style={{ gap: 2, marginBottom: theme.spacing.sm }}>
        <AppText variant="headingSmall">{title || "Build with Fuvay"}</AppText>
        {/* Says what actually happens next. "Global services available" was
            internal wording that told the customer nothing. */}
        <AppText variant="caption" color="tertiary">
          Tell us what you need and our team calls you back
        </AppText>
      </View>

      <View style={{ gap: theme.spacing.sm }}>
        {rows.map((row, rowIndex) => (
          <View key={rowIndex} style={{ flexDirection: "row", gap: theme.spacing.sm }}>
            {row.map(service => (
              <ProjectTile key={service.id} service={service} onPress={() => setSelected(service)} />
            ))}
            {/* An equal-flex spacer keeps a lone trailing card the same width as
                the ones above rather than stretching it across the row. */}
            {row.length === 1 ? <View style={{ flex: 1 }} /> : null}
          </View>
        ))}
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

function ProjectTile({ service, onPress }: { service: GlobalService; onPress: () => void }) {
  const { theme } = useTheme();
  const accent = resolveGlobalServiceAccent(service.name);
  const artwork = service.iconUrl ? resolveMediaUrl(service.iconUrl) : null;

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`${service.name}, request a callback`}
      style={({ pressed }) => ({
        flex: 1,
        gap: theme.spacing.xs,
        padding: theme.spacing.base,
        borderRadius: theme.radiusUsage.card,
        // The offering's own colour as a wash, so the tile keeps its identity
        // without the full-bleed card competing with the rest of the screen.
        backgroundColor: `${accent.background}14`,
        borderWidth: 1, borderColor: `${accent.background}33`,
        opacity: pressed ? 0.88 : 1,
      })}
    >
      <View
        style={{
          width: 40, height: 40, borderRadius: theme.radiusUsage.input,
          alignItems: "center", justifyContent: "center", overflow: "hidden",
          backgroundColor: `${accent.background}26`,
        }}
      >
        {artwork ? (
          <Image
            source={{ uri: artwork }}
            style={{ width: "100%", height: "100%" }}
            resizeMode="contain"
            accessibilityElementsHidden
          />
        ) : (
          // Admin artwork wins; this only varies the fallback so the section is
          // not a column of identical glyphs.
          <Icon
            name={resolveGlobalServiceIcon(service.name)}
            size="standard"
            color={accent.background}
            decorative
          />
        )}
      </View>

      <AppText variant="bodyStrong" numberOfLines={2}>{service.name}</AppText>
      {service.tagline ? (
        <AppText variant="caption" color="secondary" numberOfLines={2}>{service.tagline}</AppText>
      ) : null}

      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs, marginTop: theme.spacing.xxs }}>
        <AppText variant="labelStrong" style={{ color: accent.background }}>Get a callback</AppText>
        <Icon name="arrow-forward" size="compact" color={accent.background} decorative />
      </View>
    </Pressable>
  );
}
