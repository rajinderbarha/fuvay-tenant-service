import React, { useEffect, useMemo, useState } from "react";
import { ImageBackground, NativeScrollEvent, NativeSyntheticEvent, Pressable, ScrollView, useWindowDimensions, View } from "react-native";

import { useGlobalServicesQuery } from "../../api/globalServices/useGlobalServicesQuery";
import { useTheme } from "../../design-system/theme";
import { GlobalService } from "../../domain/globalServices";
import { HomeCampaign } from "../../domain/customerHome";
import { resolveMediaUrl } from "../../domain/mediaUrl";
import { AppText } from "../AppText";
import { Icon } from "../Icon";
import { GlobalServiceInquiryModal } from "./GlobalServiceInquiryModal";

const DIGITAL_STUDIO_IMAGE = require("../../../assets/fuvay-digital-studio.png");

export interface GlobalServicesSectionProps {
  defaultZipcode?: string | null;
  title?: string | null;
  /** Increment to open the primary nationwide-service brief from another Home placement. */
  openRequestToken?: number;
  variant?: "compact_services" | "studio_rail" | string;
  campaigns?: HomeCampaign[];
}

/** Nationwide work is independent from local provider serviceability. */
export function GlobalServicesSection({ defaultZipcode, title = "Build with Fuvay", openRequestToken = 0, variant = "compact_services", campaigns = [] }: GlobalServicesSectionProps) {
  const { theme } = useTheme();
  const { width } = useWindowDimensions();
  const query = useGlobalServicesQuery();
  const [selected, setSelected] = useState<GlobalService | null>(null);
  const [campaignIndex, setCampaignIndex] = useState(0);
  const services = useMemo(() => query.data ?? [], [query.data]);
  const primary = useMemo(
    () => services.find(service => /web|mobile|software|ai/i.test(service.name)) ?? services[0] ?? null,
    [services],
  );

  useEffect(() => {
    if (openRequestToken > 0 && primary) setSelected(primary);
  }, [openRequestToken, primary]);

  function openPrimary() {
    if (primary) setSelected(primary);
    else void query.refetch();
  }

  if (variant === "compact_services") {
    const bannerWidth = Math.min(width, 560) - theme.spacing.base * 2;
    return (
      <View accessibilityLabel="Fuvay digital services">
        <View style={{ marginBottom: theme.spacing.sm, flexDirection: "row", alignItems: "baseline" }}>
          <AppText variant="headingSmall">{title}</AppText>
          <AppText variant="caption" color="secondary" style={{ marginLeft: theme.spacing.sm, flex: 1 }}>Global services Available</AppText>
          <Pressable onPress={openPrimary} accessibilityRole="button" accessibilityLabel="See all global services" style={{ minHeight: 36, justifyContent: "center" }}>
            <AppText variant="bodySmall" style={{ color: theme.colors.brandPrimary, fontWeight: "800" }}>See All</AppText>
          </Pressable>
        </View>
        {campaigns.length ? (
          <>
            <ScrollView
              horizontal
              pagingEnabled
              bounces={false}
              showsHorizontalScrollIndicator={false}
              onMomentumScrollEnd={(event: NativeSyntheticEvent<NativeScrollEvent>) => setCampaignIndex(Math.round(event.nativeEvent.contentOffset.x / bannerWidth))}
            >
              {campaigns.map(campaign => (
                <Pressable key={campaign.campaignId} onPress={openPrimary} accessibilityRole="button" accessibilityLabel={`${campaign.actionLabel}: ${campaign.title}`} style={({ pressed }) => ({ width: bannerWidth, opacity: pressed ? .86 : 1 })}>
                  <ImageBackground source={{ uri: resolveMediaUrl(campaign.imageUrl)! }} resizeMode="cover" style={{ width: bannerWidth, height: 142, overflow: "hidden", borderRadius: 14, backgroundColor: "#6424C7" }} accessibilityIgnoresInvertColors>
                    <View style={{ flex: 1, width: "60%", padding: theme.spacing.base, justifyContent: "center" }}>
                      <AppText variant="headingSmall" numberOfLines={2} style={{ color: "#FFFFFF", fontSize: 20, lineHeight: 24 }}>{campaign.title}</AppText>
                      <AppText variant="caption" numberOfLines={2} style={{ color: "rgba(255,255,255,.82)", marginTop: 4 }}>{campaign.subtitle}</AppText>
                      <View style={{ marginTop: theme.spacing.md, flexDirection: "row", alignItems: "center", gap: 6 }}>
                        <AppText variant="caption" style={{ color: "#FFFFFF", fontWeight: "800" }}>{campaign.actionLabel}</AppText>
                        <Icon name="arrow-forward-circle" size="compact" color="#FFFFFF" decorative />
                      </View>
                    </View>
                  </ImageBackground>
                </Pressable>
              ))}
            </ScrollView>
            {campaigns.length > 1 ? (
              <View style={{ height: 22, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 5 }}>
                {campaigns.map((campaign, index) => <View key={campaign.campaignId} style={{ width: index === campaignIndex ? 20 : 7, height: 4, borderRadius: 2, backgroundColor: index === campaignIndex ? theme.colors.brandPrimary : theme.colors.borderStrong }} />)}
              </View>
            ) : null}
          </>
        ) : (
          <Pressable onPress={openPrimary} accessibilityRole="button" style={{ height: 142, borderRadius: 14, overflow: "hidden" }}>
            <ImageBackground source={DIGITAL_STUDIO_IMAGE} resizeMode="cover" style={{ flex: 1 }}>
              <View style={{ flex: 1, padding: theme.spacing.base, justifyContent: "center", backgroundColor: theme.colors.mediaScrim }}><AppText variant="headingSmall" style={{ color: "#FFFFFF" }}>Web Development</AppText><AppText variant="caption" style={{ color: "#FFFFFF", marginTop: 4 }}>Modern, fast & scalable web solutions</AppText></View>
            </ImageBackground>
          </Pressable>
        )}
        <GlobalServiceInquiryModal service={selected} defaultZipcode={defaultZipcode} onClose={() => setSelected(null)} />
      </View>
    );
  }

  return (
    <View accessibilityLabel="Fuvay digital services">
      {title ? (
        <AppText variant="headingMedium" style={{ marginBottom: theme.spacing.sm }}>{title}</AppText>
      ) : null}
      <Pressable
        onPress={openPrimary}
        accessibilityRole="button"
        accessibilityLabel={primary ? `Start a ${primary.name} project with Fuvay` : "Load Fuvay digital services"}
        style={({ pressed }) => ({ opacity: pressed ? 0.9 : 1 })}
      >
        <ImageBackground
          source={DIGITAL_STUDIO_IMAGE}
          resizeMode="cover"
          style={{ height: 152, overflow: "hidden", borderRadius: 18 }}
          accessibilityIgnoresInvertColors
        >
          <View style={{ flex: 1, padding: theme.spacing.base, justifyContent: "space-between", backgroundColor: theme.colors.mediaScrimStrong }}>
            <View>
              <View style={{ alignSelf: "flex-start", paddingHorizontal: 8, paddingVertical: 4, backgroundColor: theme.colors.campaignAccent }}>
                <AppText variant="caption" style={{ color: theme.colors.campaignBadgeForeground, fontWeight: "800" }}>AVAILABLE NATIONWIDE</AppText>
              </View>
              <AppText variant="headingMedium" numberOfLines={1} style={{ color: theme.colors.mediaForeground, marginTop: theme.spacing.xs, fontSize: 22 }}>
                Fuvay Digital Studio
              </AppText>
              <AppText variant="bodySmall" style={{ color: theme.colors.mediaForegroundMuted, marginTop: 2 }}>
                Web · Mobile · Software · AI
              </AppText>
            </View>
            <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
              <View style={{ maxWidth: "65%" }}>
                <AppText variant="bodyStrong" style={{ color: theme.colors.mediaForeground }}>Build your next digital product</AppText>
                <AppText variant="caption" numberOfLines={1} style={{ color: theme.colors.mediaForegroundMuted }}>A specialist will reply to your brief.</AppText>
              </View>
              <View style={{ minHeight: 36, paddingHorizontal: theme.spacing.md, flexDirection: "row", alignItems: "center", gap: 4, backgroundColor: theme.colors.surfaceDefault }}>
                <AppText variant="caption" style={{ color: theme.colors.textPrimary, fontWeight: "800" }}>Start brief</AppText>
                <Icon name="arrow-forward" size="compact" color={theme.colors.textPrimary} decorative />
              </View>
            </View>
          </View>
        </ImageBackground>
      </Pressable>

      {services.length > 1 ? (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingTop: theme.spacing.sm, gap: theme.spacing.sm }}>
          {services.map(service => (
            <Pressable
              key={service.id}
              onPress={() => setSelected(service)}
              accessibilityRole="button"
              accessibilityLabel={`Discuss ${service.name}`}
            style={({ pressed }) => ({ width: 176, minHeight: 76, paddingHorizontal: theme.spacing.sm, flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, borderWidth: 1, borderColor: theme.colors.borderSubtle, borderRadius: 16, backgroundColor: theme.colors.surfaceDefault, opacity: pressed ? 0.72 : 1 })}
            >
              <View style={{ width: 38, height: 38, alignItems: "center", justifyContent: "center", overflow: "hidden", backgroundColor: theme.colors.accentVioletSurface }}>
                <Icon name={serviceIcon(service.name)} size="standard" color={theme.colors.accentViolet} decorative />
              </View>
              <AppText variant="caption" numberOfLines={2} style={{ flex: 1, fontWeight: "700" }}>{service.name}</AppText>
            </Pressable>
          ))}
        </ScrollView>
      ) : null}

      <GlobalServiceInquiryModal service={selected} defaultZipcode={defaultZipcode} onClose={() => setSelected(null)} />
    </View>
  );
}

function serviceIcon(name: string): React.ComponentProps<typeof Icon>["name"] {
  if (/mobile|app/i.test(name)) return "phone-portrait";
  if (/web/i.test(name)) return "globe";
  if (/ai|machine/i.test(name)) return "sparkles";
  if (/data|analyt/i.test(name)) return "analytics";
  if (/blockchain/i.test(name)) return "cube";
  return "code-slash";
}
