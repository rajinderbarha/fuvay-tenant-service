import React, { useEffect, useRef, useState } from "react";
import { View, TextInput, Animated, Easing, AccessibilityInfo } from "react-native";
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

const HOLD_MS = 2000;
const SLIDE_MS = 500;
/** The strip's line height. Fixed rather than measured because it has to clip to
 * exactly one line for the effect to read as scrolling rather than as two words
 * briefly overlapping. */
const LINE_HEIGHT = 22;

/**
 * Full-width elevated search field.
 *
 * The word "Search" stays put and only the service name moves, scrolling up out of
 * view as the next one rises into it. Deliberately not a cross-fade: the fixed word
 * keeps the box reading as a search box at every frame, and vertical motion reads as
 * a list of things the customer could search for rather than as text flickering.
 *
 * Every suggestion is rendered once into a tall strip, with the FIRST one repeated at
 * the end, and the strip is scrolled by one line at a time. That is what makes the
 * loop seamless: when the run reaches the repeated copy the position is snapped back
 * to the top, and since that copy is pixel-identical to the real first item, the snap
 * is invisible.
 *
 * The earlier version swapped a two-word window on each step, resetting the offset in
 * the animation callback. The reset lands on the UI thread immediately while the React
 * re-render that supplies the next word lands a frame later, so the outgoing word
 * flashed back into place for one frame -- the visible jerk. Nothing here re-renders
 * during the animation at all.
 *
 * Rotation stops entirely once the field has focus or any text — a moving hint under a
 * caret is a distraction — and never starts under reduced motion or with a screen
 * reader active, where a silently-changing label would be re-announced repeatedly.
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
  /** Which line of the strip is on screen, as a float so it can be animated. */
  const position = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    AccessibilityInfo.isScreenReaderEnabled().then(setScreenReaderOn).catch(() => {});
    const sub = AccessibilityInfo.addEventListener("screenReaderChanged", setScreenReaderOn);
    return () => sub.remove();
  }, []);

  const items = suggestions ?? [];
  const count = items.length;
  const rotating =
    count > 1 && !focused && value.length === 0 && !reduceMotion && !screenReaderOn;

  useEffect(() => {
    if (!rotating) return;
    let cancelled = false;
    let current: Animated.CompositeAnimation | null = null;

    const step = (line: number) => {
      if (cancelled) return;
      current = Animated.sequence([
        Animated.delay(HOLD_MS),
        Animated.timing(position, {
          toValue: line + 1,
          duration: SLIDE_MS,
          // Eased both ends, so a word settles rather than stopping dead. A linear
          // slide is what makes a ticker feel mechanical.
          easing: Easing.inOut(Easing.cubic),
          useNativeDriver: true,
        }),
      ]);
      current.start(({ finished }) => {
        if (cancelled || !finished) return;
        // Landed on the repeated first item: snap to the real one. Identical pixels,
        // so there is nothing to see, and the next run starts from the top again
        // instead of the strip creeping away forever.
        const next = line + 1 >= count ? 0 : line + 1;
        if (next === 0) position.setValue(0);
        step(next);
      });
    };

    step(0);
    return () => {
      cancelled = true;
      current?.stop();
      position.setValue(0);
    };
  }, [rotating, count, position]);

  const showAnimated = count > 0 && !focused && value.length === 0;

  // One extra line for the repeated first item, so the interpolation covers the
  // full strip including the seam.
  const translateY = position.interpolate({
    inputRange: [0, Math.max(1, count)],
    outputRange: [0, -LINE_HEIGHT * Math.max(1, count)],
  });

  const wordStyle = {
    height: LINE_HEIGHT,
    lineHeight: LINE_HEIGHT,
    color: theme.colors.textTertiary,
    ...theme.typography.body,
  };

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
          // The rotating hint is drawn as an overlay, so the native placeholder is
          // suppressed while it is showing -- otherwise both render on top of each
          // other.
          placeholder={showAnimated ? "" : placeholder}
          placeholderTextColor={theme.colors.textTertiary}
          returnKeyType="search"
          accessibilityLabel="Search services"
          // Screen readers get the stable description, never the word that happens
          // to be on screen at that instant.
          accessibilityHint={placeholder}
          style={{ color: theme.colors.textPrimary, ...theme.typography.body }}
        />
        {showAnimated ? (
          <View
            pointerEvents="none"
            accessibilityElementsHidden
            importantForAccessibility="no-hide-descendants"
            style={{ position: "absolute", left: 0, right: 0, flexDirection: "row" }}
          >
            <Animated.Text style={wordStyle}>Search </Animated.Text>
            {/* One line tall and clipped: the outgoing and incoming words are never
                both visible, which is what separates a scroll from a glitch. */}
            <View style={{ flex: 1, height: LINE_HEIGHT, overflow: "hidden" }}>
              <Animated.View style={{ transform: [{ translateY }] }}>
                {[...items, items[0]].map((word, i) => (
                  // Index-keyed on purpose: this is a positional strip, and the first
                  // word deliberately appears twice, so its name is not a unique key.
                  <Animated.Text key={`${i}-${word}`} numberOfLines={1} style={wordStyle}>
                    {`${word}…`}
                  </Animated.Text>
                ))}
              </Animated.View>
            </View>
          </View>
        ) : null}
      </View>
    </View>
  );
}
