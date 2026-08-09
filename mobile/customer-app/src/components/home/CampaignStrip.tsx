import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";
import { HomeCampaign } from "../../domain/customerHome";
import { formatCampaignEnds } from "../../domain/campaignWindow";

export interface CampaignStripProps {
  campaign: HomeCampaign;
  isCtaRoutable: (campaign: HomeCampaign) => boolean;
  onPressCta: (campaign: HomeCampaign) => void;
}

/**
 * The quiet banner: one line, one accent, tappable end to end.
 *
 * The point of this style is restraint. Not every message deserves a hero card
 * with artwork -- "same-day slots are open" is useful precisely when it does not
 * interrupt, and a screen where every banner shouts trains customers to skip all
 * of them. So there is no artwork, no description, and no button: the row itself
 * is the target when its link resolves, and it degrades to plain text when it
 * does not, rather than looking pressable and doing nothing.
 */
export function CampaignStrip({ campaign, isCtaRoutable, onPressCta }: CampaignStripProps) {
  const { theme } = useTheme();
  const accent = campaign.accentColor || theme.colors.brandPrimaryStrong;
  const routable = isCtaRoutable(campaign);
  const endsLabel = formatCampaignEnds(campaign.endsAt);

  const body = (
    <View
      style={{
        flexDirection: "row", alignItems: "center", gap: theme.spacing.sm,
        paddingHorizontal: theme.spacing.base, paddingVertical: theme.spacing.sm,
        borderRadius: theme.radiusUsage.card,
        backgroundColor: `${accent}14`,
        borderWidth: 1, borderColor: `${accent}3D`,
      }}
    >
      <View
        style={{
          width: 32, height: 32, borderRadius: theme.radiusUsage.input,
          alignItems: "center", justifyContent: "center",
          backgroundColor: `${accent}29`,
        }}
      >
        <Icon name="flash-outline" size="compact" color={accent} decorative />
      </View>
      <View style={{ flex: 1, minWidth: 0 }}>
        <AppText variant="bodySmall" numberOfLines={2}>{campaign.title}</AppText>
        {endsLabel ? <AppText variant="caption" color="tertiary">{endsLabel}</AppText> : null}
      </View>
      {routable ? (
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}>
          {campaign.ctaLabel ? (
            <AppText variant="labelStrong" style={{ color: accent }}>{campaign.ctaLabel}</AppText>
          ) : null}
          <Icon name="chevron-forward" size="compact" color={accent} decorative />
        </View>
      ) : null}
    </View>
  );

  if (!routable) return body;

  return (
    <Pressable
      onPress={() => onPressCta(campaign)}
      accessibilityRole="button"
      accessibilityLabel={campaign.ctaLabel ? `${campaign.title}. ${campaign.ctaLabel}` : campaign.title}
      style={({ pressed }) => ({ opacity: pressed ? 0.85 : 1 })}
    >
      {body}
    </Pressable>
  );
}
