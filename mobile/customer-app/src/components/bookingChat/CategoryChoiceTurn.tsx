import React from "react";
import { Pressable, View } from "react-native";

import { useTheme } from "../../design-system/theme";
import type { HomeCategory, HomeServiceGroup } from "../../domain/customerHome";
import { AppLucideIcon } from "../AppLucideIcon";
import { FuvayIcon } from "../FuvayIcon";
import { BotText } from "./BotText";

export interface CategoryChoiceTurnProps {
  categories: HomeCategory[];
  serviceGroups?: HomeServiceGroup[];
  loading: boolean;
  city: string | null;
  zipcode?: string | null;
  onSelect: (category: HomeCategory) => void;
  onSelectGroup?: (group: HomeServiceGroup) => void;
}

/** Backend-driven choices presented using the approved assistant bubble/chip pattern. */
export function CategoryChoiceTurn({
  categories,
  serviceGroups = [],
  loading,
  city,
  zipcode,
  onSelect,
  onSelectGroup,
}: CategoryChoiceTurnProps) {
  const { theme } = useTheme();
  const choices = serviceGroups.length
    ? serviceGroups.map(group => ({ id: group.serviceGroupId, name: group.name, select: () => onSelectGroup?.(group) }))
    : categories.map(category => ({ id: category.categoryId, name: category.name, select: () => onSelect(category) }));
  const locationLabel = city ? [city, zipcode].filter(Boolean).join(" · ") : zipcode ?? "Saved service location";
  const headline = loading ? "Finding services near you" : choices.length ? "Which service do you need?" : "Let's get your location ready";

  return (
    <View style={{ gap: 14 }}>
      <View style={{ flexDirection: "row", alignItems: "flex-start", gap: 10 }}>
        <View style={{ width: 32, height: 32, borderRadius: 16, backgroundColor: theme.fuvay.surfaces.card, borderWidth: 1, borderColor: theme.fuvay.surfaces.edge, alignItems: "center", justifyContent: "center" }}>
          <FuvayIcon size={17} accessibilityLabel="Fuvay booking assistant" />
        </View>
        <View style={{ flex: 1, minWidth: 0, paddingHorizontal: 15, paddingVertical: 13, borderRadius: 18, borderTopLeftRadius: 4, backgroundColor: theme.fuvay.surfaces.card, borderWidth: 1, borderColor: theme.fuvay.surfaces.edge }}>
          <BotText style={{ fontSize: 14.5, lineHeight: 19, fontWeight: "600", color: theme.fuvay.surfaces.text }}>{headline}</BotText>
          {!loading && choices.length ? <BotText style={{ marginTop: 5, fontSize: 11.5, lineHeight: 17, color: theme.fuvay.surfaces.sub }}>Pick one and I'll ask only the questions needed to book it.</BotText> : null}
        </View>
      </View>

      {loading ? (
        <View accessibilityRole="progressbar" accessibilityLabel="Finding available services" style={{ marginLeft: 42, alignSelf: "flex-start", flexDirection: "row", gap: 5, paddingHorizontal: 16, paddingVertical: 14, borderRadius: 18, borderTopLeftRadius: 4, backgroundColor: theme.fuvay.surfaces.card, borderWidth: 1, borderColor: theme.fuvay.surfaces.edge }}>
          {[0, 1, 2].map(dot => <View key={dot} style={{ width: 7, height: 7, borderRadius: 4, backgroundColor: theme.fuvay.accents.a2 }} />)}
        </View>
      ) : choices.length ? (
        <View style={{ marginLeft: 42, flexDirection: "row", flexWrap: "wrap", justifyContent: "flex-end", gap: 8 }}>
          {choices.map(choice => (
            <Pressable key={choice.id} onPress={choice.select} accessibilityRole="button" accessibilityLabel={`Book ${choice.name}`} style={({ pressed }) => ({ minHeight: 40, paddingHorizontal: 16, borderRadius: 99, borderWidth: 1.2, borderColor: theme.fuvay.accents.a2, backgroundColor: pressed ? theme.fuvay.accents.a2 : theme.fuvay.surfaces.card, flexDirection: "row", alignItems: "center", gap: 7 })}>
              {({ pressed }) => <><AppLucideIcon name="tools" size={13} color={pressed ? theme.fuvay.ink(theme.fuvay.accents.a2) : theme.fuvay.accents.a2} /><BotText style={{ fontSize: 12.5, fontWeight: "600", color: pressed ? theme.fuvay.ink(theme.fuvay.accents.a2) : theme.fuvay.accents.a2 }}>{choice.name}</BotText></>}
            </Pressable>
          ))}
        </View>
      ) : (
        <View style={{ marginLeft: 42, padding: 15, borderRadius: 18, backgroundColor: theme.fuvay.surfaces.card, borderWidth: 1, borderColor: theme.fuvay.surfaces.edge }}>
          <BotText style={{ fontSize: 13, color: theme.fuvay.surfaces.sub }}>No services are available here yet. Change your service location on Home.</BotText>
        </View>
      )}

      <View style={{ marginLeft: 42, flexDirection: "row", alignItems: "center", gap: 7, paddingTop: 4 }}>
        <AppLucideIcon name="map-marker-path" size={12} color={theme.fuvay.surfaces.faint} />
        <BotText style={{ flex: 1, fontSize: 10.5, color: theme.fuvay.surfaces.faint }}>{locationLabel}</BotText>
      </View>
    </View>
  );
}
