import React from "react";
import { Image, Pressable, View } from "react-native";

import type { HomeServiceGroup } from "../../domain/customerHome";
import { customerExperienceCopy } from "../../content/customerExperience";
import { useTheme } from "../../design-system/theme";
import { AppIconTile, type AppIconTileTone } from "../AppIconTile";
import { type AppLucideName } from "../AppLucideIcon";
import { AppSurface } from "../AppSurface";
import { AppText } from "../AppText";

const SPECIALIST_ICONS: readonly AppLucideName[] = [
  "air-conditioner",
  "pipe-wrench",
  "lightning-bolt-outline",
  "spray-bottle",
  "washing-machine",
  "home-lightning-bolt-outline",
  "water-circle",
  "stove",
  "tools",
];

const SPECIALIST_TONES: readonly AppIconTileTone[] = ["cyan", "mint", "amber", "violet"];

export function HomeOfferCard({ onPress }: { onPress: () => void }) {
  const { theme } = useTheme();
  const copy = customerExperienceCopy.home.offer;
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={`${copy.action}: ${copy.title}`} style={({ pressed }) => ({ opacity: pressed ? theme.opacity.pressed : 1 })}>
      <AppSurface variant="raised" style={{ minHeight: theme.metrics.media.campaign, borderRadius: theme.radiusUsage.card, overflow: "hidden", flexDirection: "row" }}>
        <View style={{ width: "40%", minHeight: theme.metrics.media.campaign }}>
          <Image source={require("../../../assets/home-campaigns/fuvay-ac-care-hero-v1.png")} resizeMode="cover" style={{ width: "100%", height: "100%" }} accessibilityIgnoresInvertColors />
          <View style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: theme.spacing.xs, backgroundColor: theme.colors.accentAmber }} />
        </View>
        <View style={{ flex: 1, padding: theme.spacing.base, justifyContent: "center", gap: theme.spacing.sm }}>
          <AppText variant="metaLabel" style={{ color: theme.colors.accentAmber }}>{copy.eyebrow}</AppText>
          <AppText variant="headingSmall">{copy.title}</AppText>
          <View style={{ width: theme.spacing.xxl, height: theme.spacing.xxs, backgroundColor: theme.colors.accentAmber }} />
          <AppText variant="caption" color="secondary">{copy.subtitle}</AppText>
          <View style={{ alignSelf: "flex-start", minHeight: theme.metrics.control.compact, paddingHorizontal: theme.spacing.base, borderRadius: theme.radiusUsage.button, backgroundColor: theme.colors.accentAmber, justifyContent: "center" }}>
            <AppText variant="button" style={{ color: theme.colors.campaignBadgeForeground }}>{copy.action}</AppText>
          </View>
        </View>
      </AppSurface>
    </Pressable>
  );
}

export function HomeSpecialistsGrid({ groups, onPress }: { groups: HomeServiceGroup[]; onPress: (group: HomeServiceGroup) => void }) {
  const { theme } = useTheme();
  const copy = customerExperienceCopy.home;
  return (
    <AppSurface variant="raised" style={{ padding: theme.spacing.lg, borderRadius: theme.radiusUsage.panel, overflow: "hidden" }}>
      <AppText variant="headingSmall">{copy.sections.specialists}</AppText>
      <AppText variant="bodySmall" color="secondary" style={{ marginTop: theme.spacing.xxs }}>{copy.specialistSubtitle}</AppText>
      <View style={{ marginTop: theme.spacing.base, flexDirection: "row", flexWrap: "wrap", rowGap: theme.spacing.lg }}>
        {groups.slice(0, SPECIALIST_ICONS.length).map((group, index) => (
          <Pressable key={group.serviceGroupId} onPress={() => onPress(group)} accessibilityRole="button" accessibilityLabel={`Book ${group.name}`} style={({ pressed }) => ({ width: "33.333%", alignItems: "center", gap: theme.spacing.sm, opacity: pressed ? theme.opacity.pressed : 1 })}>
            <AppIconTile name={SPECIALIST_ICONS[index % SPECIALIST_ICONS.length]} size={theme.metrics.tile.specialist} shape="circle" tone={SPECIALIST_TONES[index % SPECIALIST_TONES.length]} />
            <AppText variant="caption" align="center" numberOfLines={2} style={{ paddingHorizontal: theme.spacing.xs }}>{group.name}</AppText>
          </Pressable>
        ))}
      </View>
    </AppSurface>
  );
}
