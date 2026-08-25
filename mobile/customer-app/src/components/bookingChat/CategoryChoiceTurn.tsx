import React from "react";
import { ActivityIndicator, Pressable, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { useTheme } from "../../design-system/theme";
import { resolveCategoryIcon } from "../../domain/categoryIcon";
import { HomeCategory, HomeServiceGroup } from "../../domain/customerHome";
import { FuvayIcon } from "../FuvayIcon";
import { Icon } from "../Icon";
import { useBotColors } from "./botTheme";

export interface CategoryChoiceTurnProps {
  categories: HomeCategory[];
  serviceGroups?: HomeServiceGroup[];
  loading: boolean;
  city: string | null;
  zipcode?: string | null;
  onSelect: (category: HomeCategory) => void;
  onSelectGroup?: (group: HomeServiceGroup) => void;
}

/** Backend-driven service chooser. Service groups are preferred because a
 * broad category such as Home Services must not mix unrelated appliances. */
export function CategoryChoiceTurn({
  categories, serviceGroups = [], loading, city, zipcode, onSelect, onSelectGroup,
}: CategoryChoiceTurnProps) {
  const BOT = useBotColors();
  const { theme } = useTheme();
  const choices = serviceGroups.length > 0
    ? serviceGroups.map(group => ({
        id: group.serviceGroupId,
        name: group.name,
        slug: group.slug,
        iconUrl: group.iconUrl,
        select: () => onSelectGroup?.(group),
      }))
    : categories.map(category => ({
        id: category.categoryId,
        name: category.name,
        slug: category.slug,
        iconUrl: category.iconUrl,
        select: () => onSelect(category),
      }));
  const locationLabel = city ? [city, zipcode].filter(Boolean).join(" · ") : zipcode ?? "Saved service location";
  const headline = loading ? "Finding services near you" : choices.length > 0 ? "Which service do you need?" : "Let's get your location ready";

  return (
    <View style={{ gap: theme.spacing.xl }}>
      <View style={{ paddingVertical: theme.spacing.sm }}>
        <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.md }}>
          <View style={{ width: 48, height: 48, borderRadius: 14, backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: BOT.border, alignItems: "center", justifyContent: "center" }}>
            <FuvayIcon size={32} accessibilityLabel="Fuvay booking assistant" />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={{ fontSize: 11, fontWeight: "800", color: BOT.brandLight, letterSpacing: 1.1 }}>ASK FUVAY</Text>
            <Text style={{ marginTop: 4, fontSize: 26, lineHeight: 31, fontWeight: "800", color: BOT.textPrimary }}>{headline}</Text>
            <Text style={{ marginTop: 6, fontSize: 14, lineHeight: 20, color: BOT.textSecondary }}>
              Pick a service and we'll show only its relevant problems and booking questions.
            </Text>
          </View>
        </View>
        <View style={{ marginTop: theme.spacing.md, alignSelf: "flex-start", flexDirection: "row", alignItems: "center", gap: theme.spacing.xs, paddingHorizontal: theme.spacing.sm, paddingVertical: theme.spacing.xs, borderRadius: theme.radius.radiusFull, backgroundColor: BOT.surfaceSunken }}>
          <Ionicons name="location-outline" size={14} color={BOT.brandLight} />
          <Text style={{ fontSize: 12, fontWeight: "700", color: BOT.textSecondary }}>{locationLabel}</Text>
        </View>
      </View>

      {loading ? (
        <View style={{ minHeight: 132, alignItems: "center", justifyContent: "center", gap: theme.spacing.sm, borderRadius: 18, backgroundColor: BOT.surface, borderWidth: 1, borderColor: BOT.borderSubtle }}>
          <ActivityIndicator size="small" color={BOT.brand} />
          <Text style={{ fontSize: 14, color: BOT.textMuted }}>Checking what's available near you...</Text>
        </View>
      ) : choices.length === 0 ? (
        <View style={{ padding: theme.spacing.lg, borderRadius: 18, backgroundColor: BOT.surface, borderWidth: 1, borderColor: BOT.borderSubtle }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
            <View style={{ width: 40, height: 40, borderRadius: 14, alignItems: "center", justifyContent: "center", backgroundColor: theme.colors.statusWarningSurface }}>
              <Ionicons name="location-outline" size={20} color={theme.colors.statusWarning} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={{ fontSize: 16, fontWeight: "800", color: BOT.textPrimary }}>No services here yet</Text>
              <Text style={{ marginTop: 3, fontSize: 14, lineHeight: 20, color: BOT.textMuted }}>
                {city ? `We aren't serving ${city} yet. Change your location on Home to see what's available.` : "Change your location on Home to see what's available."}
              </Text>
            </View>
          </View>
        </View>
      ) : (
        <View style={{ gap: theme.spacing.md }}>
          <View style={{ flexDirection: "row", alignItems: "flex-end", justifyContent: "space-between" }}>
            <View>
              <Text style={{ fontSize: 18, fontWeight: "800", color: BOT.textPrimary }}>Services near you</Text>
              <Text style={{ marginTop: 2, fontSize: 13, color: BOT.textMuted }}>Choose one to begin</Text>
            </View>
            <Text style={{ fontSize: 12, fontWeight: "700", color: BOT.textSecondary }}>{choices.length} available</Text>
          </View>

          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.sm }}>
            {choices.map(choice => {
              return (
                <Pressable
                  key={choice.id}
                  onPress={choice.select}
                  accessibilityRole="button"
                  accessibilityLabel={`Book ${choice.name}`}
                  style={({ pressed }) => ({
                    width: "48%", minHeight: 102, padding: theme.spacing.sm,
                    borderRadius: 14, backgroundColor: pressed ? BOT.surfaceRaised : BOT.surface,
                    borderWidth: 1, borderColor: pressed ? BOT.borderActive : BOT.borderSubtle,
                    opacity: pressed ? 0.82 : 1,
                  })}
                >
                  <View style={{ width: 42, height: 42, borderRadius: 21, alignItems: "center", justifyContent: "center", backgroundColor: BOT.surfaceSunken }}>
                    <Icon name={resolveServiceChoiceIcon(choice.name, choice.slug)} size="standard" color={BOT.brandLight} decorative />
                  </View>
                  <Text style={{ marginTop: theme.spacing.xs, paddingRight: 24, fontSize: 14, lineHeight: 18, fontWeight: "700", color: BOT.textPrimary }} numberOfLines={2}>{choice.name}</Text>
                  <View style={{ position: "absolute", right: 10, top: 10, width: 24, height: 24, borderRadius: 12, alignItems: "center", justifyContent: "center", backgroundColor: BOT.surfaceSunken }}>
                    <Ionicons name="arrow-forward" size={15} color={BOT.textSecondary} />
                  </View>
                </Pressable>
              );
            })}
          </View>
        </View>
      )}

      <View style={{ flexDirection: "row", alignItems: "center", paddingVertical: theme.spacing.md, borderTopWidth: 1, borderTopColor: BOT.borderSubtle }}>
        <Assurance icon="shield-checkmark-outline" label="Verified" />
        <Assurance icon="receipt-outline" label="Clear pricing" />
        <Assurance icon="navigate-outline" label="Tracked" />
      </View>
    </View>
  );
}

function resolveServiceChoiceIcon(name: string, slug: string | null): React.ComponentProps<typeof Icon>["name"] {
  if (/air|\bac\b|cool/i.test(name)) return "snow-outline";
  if (/geyser|heater/i.test(name)) return "flame-outline";
  if (/refriger|fridge/i.test(name)) return "cube-outline";
  if (/washing/i.test(name)) return "refresh-circle-outline";
  if (/chimney|hob|kitchen/i.test(name)) return "restaurant-outline";
  if (/purifier|\bro\b|water/i.test(name)) return "water-outline";
  return resolveCategoryIcon(slug);
}

function Assurance({ icon, label }: { icon: React.ComponentProps<typeof Ionicons>["name"]; label: string }) {
  const BOT = useBotColors();
  return (
    <View style={{ alignItems: "center", gap: 3, flex: 1 }}>
      <Ionicons name={icon} size={17} color={BOT.brandLight} />
      <Text style={{ fontSize: 11, fontWeight: "700", color: BOT.textSecondary }}>{label}</Text>
    </View>
  );
}
