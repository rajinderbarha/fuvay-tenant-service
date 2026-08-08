import React from "react";
import { View, Text, ActivityIndicator } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useBotColors } from "./botTheme";
import { BotAssistantBubble, BotOptionChips } from "./BotPrimitives";
import { HomeCategory } from "../../domain/customerHome";

export interface CategoryChoiceTurnProps {
  /** The real, ZIP-scoped bookable categories -- the same backend list Home
   * renders its service cards from. Never a hardcoded menu. */
  categories: HomeCategory[];
  loading: boolean;
  city: string | null;
  onSelect: (category: HomeCategory) => void;
}

/**
 * The first turn when the assistant is opened from the tab bar rather than
 * from a service on Home.
 *
 * Two things were wrong before. The tab carried the params of whatever service
 * had last been tapped on Home, so a bare tab tap opened straight into that
 * category's questions -- AC questions for a customer who had asked for
 * nothing. And with those params cleared there was nothing here at all: the
 * category-less branch of the controller sets `ready` and renders no turn, no
 * options and no usable composer, which is a dead screen.
 *
 * So the assistant now asks the question it should have asked: which service.
 * Choosing one starts exactly the same category-scoped conversation a tap on
 * Home would have.
 */
export function CategoryChoiceTurn({ categories, loading, city, onSelect }: CategoryChoiceTurnProps) {
  const BOT = useBotColors();

  if (loading) {
    return (
      <BotAssistantBubble>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
          <ActivityIndicator size="small" color={BOT.brand} />
          <Text style={{ fontSize: 15, color: BOT.textMuted }}>
            Checking what's available near you…
          </Text>
        </View>
      </BotAssistantBubble>
    );
  }

  // Nothing bookable at this ZIP is a real answer, not an empty list to hide.
  if (categories.length === 0) {
    return (
      <View style={{ gap: 12 }}>
        <BotAssistantBubble text="Hi! I'm your Fuvay booking assistant." />
        <BotAssistantBubble>
          <View style={{ gap: 6 }}>
            <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
              <Ionicons name="location-outline" size={15} color={BOT.textTertiary} />
              <Text style={{ fontSize: 15, fontWeight: "700", color: BOT.textPrimary }}>
                No services here yet
              </Text>
            </View>
            <Text style={{ fontSize: 15, lineHeight: 21, color: BOT.textMuted }}>
              {city
                ? `We aren't serving ${city} yet. Change your location on Home to see what's available.`
                : "We aren't serving your area yet. Change your location on Home to see what's available."}
            </Text>
          </View>
        </BotAssistantBubble>
      </View>
    );
  }

  return (
    <View style={{ gap: 12 }}>
      <BotAssistantBubble text="Hi! I'm your Fuvay booking assistant." />
      <BotAssistantBubble text="Which service do you need?" />
      <BotOptionChips
        items={categories.map(c => c.name)}
        selected={null}
        onSelect={label => {
          const category = categories.find(c => c.name === label);
          if (category) onSelect(category);
        }}
      />
    </View>
  );
}
