import React, { useEffect, useRef, useState } from "react";
import { View, TextInput, Animated, AccessibilityInfo } from "react-native";
import { useTheme, useReducedMotion } from "../../design-system/theme";
import { Icon } from "../Icon";

export interface ServiceSearchProps {
  value: string;
  onChangeText: (value: string) => void;
  onSubmit?: () => void;
  placeholder?: string;
  /**
   * Real service names to cycle through in the placeholder, e.g.
   * ["Air Conditioning", "Plumbing", ...]. Sourced from what is actually
   * bookable at the customer's location, never a hardcoded marketing list --
   * suggesting a search term that returns nothing would be worse than no
   * suggestion at all. Falls back to the static placeholder when empty.
   */
  suggestions?: readonly string[];
}

const ROTATE_MS = 2200;
const FADE_MS = 220;

/**
 * Full-width elevated search field.
 *
 * The placeholder cycles through real bookable services so the box shows
 * what can actually be searched for, rather than a single fixed example.
 * Rotation stops entirely once the field has focus or any text — a moving
 * hint under a caret is a distraction — and never starts under reduced
 * motion or with a screen reader active, where a silently-changing label
 * would be re-announced repeatedly.
 */
export function ServiceSearch({
  value,
  onChangeText,
  onSubmit,
  placeholder = "Search AC repair, plumbing, cleaning…",
  suggestions,
}: ServiceSearchProps) {
  const { theme } = useTheme();
  const reduceMotion = useReducedMotion();
  const [screenReaderOn, setScreenReaderOn] = useState(false);
  const [focused, setFocused] = useState(false);
  const [index, setIndex] = useState(0);
  const opacity = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    AccessibilityInfo.isScreenReaderEnabled().then(setScreenReaderOn).catch(() => {});
    const sub = AccessibilityInfo.addEventListener("screenReaderChanged", setScreenReaderOn);
    return () => sub.remove();
  }, []);

  const items = suggestions ?? [];
  const rotating =
    items.length > 1 && !focused && value.length === 0 && !reduceMotion && !screenReaderOn;

  useEffect(() => {
    if (!rotating) return;
    const timer = setInterval(() => {
      // Fade out, swap the word while invisible, fade back in -- swapping
      // at full opacity reads as a flicker.
      Animated.timing(opacity, { toValue: 0, duration: FADE_MS, useNativeDriver: true }).start(() => {
        setIndex(prev => (prev + 1) % items.length);
        Animated.timing(opacity, { toValue: 1, duration: FADE_MS, useNativeDriver: true }).start();
      });
    }, ROTATE_MS);
    return () => clearInterval(timer);
  }, [rotating, items.length, opacity]);

  // Reset to the first suggestion (fully visible) whenever rotation stops,
  // so the field never sits on a half-faded word after focus or typing.
  useEffect(() => {
    if (!rotating) {
      opacity.setValue(1);
      setIndex(0);
    }
  }, [rotating, opacity]);

  const showAnimated = rotating || (items.length > 0 && !focused && value.length === 0);
  const currentSuggestion = items.length > 0 ? items[index % items.length] : null;

  return (
    <View
      style={{
        flexDirection: "row", alignItems: "center", gap: theme.spacing.sm,
        minHeight: theme.touchTargets.comfortable, paddingHorizontal: theme.spacing.base,
        borderRadius: theme.radiusUsage.input, backgroundColor: theme.colors.surfaceDefault,
        borderWidth: 1, borderColor: theme.colors.borderSubtle,
        ...theme.shadow.sm,
      }}
    >
      <Icon name="search-outline" size="standard" color={theme.colors.iconDefault} decorative />
      <View style={{ flex: 1, justifyContent: "center" }}>
        <TextInput
          value={value}
          onChangeText={onChangeText}
          onSubmitEditing={onSubmit}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          // The rotating hint is drawn as an overlay, so the native
          // placeholder is suppressed while it is showing -- otherwise both
          // render on top of each other.
          placeholder={showAnimated && currentSuggestion ? "" : placeholder}
          placeholderTextColor={theme.colors.textTertiary}
          returnKeyType="search"
          accessibilityLabel="Search services"
          // Screen readers get the stable description, never the word that
          // happens to be on screen at that instant.
          accessibilityHint={placeholder}
          style={{ color: theme.colors.textPrimary, ...theme.typography.body }}
        />
        {showAnimated && currentSuggestion ? (
          <Animated.View
            pointerEvents="none"
            accessibilityElementsHidden
            importantForAccessibility="no-hide-descendants"
            style={{ position: "absolute", left: 0, right: 0, opacity }}
          >
            <Animated.Text
              numberOfLines={1}
              style={{ color: theme.colors.textTertiary, ...theme.typography.body }}
            >
              {`Search ${currentSuggestion}…`}
            </Animated.Text>
          </Animated.View>
        ) : null}
      </View>
    </View>
  );
}
