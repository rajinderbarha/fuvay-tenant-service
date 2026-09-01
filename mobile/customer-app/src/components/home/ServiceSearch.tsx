import React, { useEffect, useRef, useState } from "react";
import { View, TextInput, Animated, Easing, AccessibilityInfo, AppState, type StyleProp, type ViewStyle } from "react-native";
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
  suggestionPrefix?: string;
  suggestionSuffix?: string;
  rightAccessory?: React.ReactNode;
  containerStyle?: StyleProp<ViewStyle>;
  appearance?: "default" | "fuvay";
}

const HOLD_MS = 2000;
const SLIDE_MS = 500;

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
  suggestionPrefix = "Search ",
  suggestionSuffix = "…",
  rightAccessory,
  containerStyle,
  appearance = "default",
}: ServiceSearchProps) {
  const { theme } = useTheme();
  const reduceMotion = useReducedMotion();
  const [screenReaderOn, setScreenReaderOn] = useState(false);
  const [focused, setFocused] = useState(false);
  const [animationGeneration, setAnimationGeneration] = useState(0);
  /** Which line of the strip is on screen, as a float so it can be animated. */
  const position = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    AccessibilityInfo.isScreenReaderEnabled().then(setScreenReaderOn).catch(() => {});
    const sub = AccessibilityInfo.addEventListener("screenReaderChanged", setScreenReaderOn);
    return () => sub.remove();
  }, []);

  // Native animations can be cancelled when iOS backgrounds the app. Restart
  // the declarative infinite loop on foreground so the placeholder never
  // freezes after the customer returns to Home.
  useEffect(() => {
    let previous = AppState.currentState;
    const sub = AppState.addEventListener("change", next => {
      if (next === "active" && previous !== "active") {
        setAnimationGeneration(current => current + 1);
      }
      previous = next;
    });
    return () => sub.remove();
  }, []);

  /**
   * The hint's own text style, taken from the SAME token the input uses, and the strip
   * height taken from that style's line height.
   *
   * Both were being set by hand: `{ height: 22, lineHeight: 22, ...typography.body }`
   * spread the token AFTER the line height, so the token's own `lineHeight` won its
   * own override and the hint could sit on a different baseline from the text it is
   * standing in for -- which reads as a different font.
   */
  const hintStyle = {
    ...theme.typography.body,
    color: appearance === "fuvay" ? theme.fuvay.surfaces.faint : theme.colors.textTertiary,
  };
  // The token always defines one; the fallback keeps TypeScript honest about the type
  // rather than pretending it cannot be absent.
  const lineHeight = theme.typography.body.lineHeight ?? 22;

  const items = suggestions ?? [];
  const count = items.length;
  const rotating =
    count > 1 && !focused && value.length === 0 && !reduceMotion && !screenReaderOn;

  useEffect(() => {
    if (!rotating) return;

    /**
     * One declarative loop: hold, slide a line, hold, slide... through the whole strip,
     * then start over from the top -- where the repeated first word means the reset is
     * invisible.
     *
     * Built as a single `Animated.loop` rather than a chain that re-armed itself from
     * each step's completion callback. That chain stopped for good the moment a step
     * reported `finished: false`, which any interruption can cause, so the hint could
     * silently freeze on one word for the rest of the session and look like no
     * animation at all. A loop has no such state to lose.
     */
    position.setValue(0);
    const animation = Animated.loop(
      Animated.sequence(
        Array.from({ length: count }, (_, line) => [
          Animated.delay(HOLD_MS),
          Animated.timing(position, {
            toValue: line + 1,
            duration: SLIDE_MS,
            // Eased both ends, so a word settles rather than stopping dead. A linear
            // slide is what makes a ticker feel mechanical.
            easing: Easing.inOut(Easing.cubic),
            useNativeDriver: true,
            isInteraction: false,
          }),
        ]).flat(),
      ),
      { iterations: -1, resetBeforeIteration: true },
    );
    animation.start();

    return () => {
      animation.stop();
      position.setValue(0);
    };
  }, [rotating, count, position, animationGeneration]);

  const showAnimated = count > 0 && !focused && value.length === 0;

  // One extra line for the repeated first item, so the interpolation covers the
  // full strip including the seam.
  const translateY = position.interpolate({
    inputRange: [0, Math.max(1, count)],
    outputRange: [0, -lineHeight * Math.max(1, count)],
  });

  return (
    <View
      style={[{
        flexDirection: "row", alignItems: "center", gap: theme.spacing.sm,
        minHeight: theme.touchTargets.comfortable, paddingHorizontal: theme.spacing.base,
        borderRadius: theme.radiusUsage.input,
        backgroundColor: appearance === "fuvay" ? theme.fuvay.surfaces.card : theme.colors.surfaceDefault,
        borderWidth: 1,
        borderColor: appearance === "fuvay" ? theme.fuvay.surfaces.edge : theme.colors.borderSubtle,
        ...theme.shadow.sm,
      }, containerStyle]}
    >
      <Icon name="search-outline" size="standard" color={appearance === "fuvay" ? theme.fuvay.surfaces.faint : theme.colors.iconDefault} decorative />
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
          placeholderTextColor={appearance === "fuvay" ? theme.fuvay.surfaces.faint : theme.colors.textTertiary}
          returnKeyType="search"
          accessibilityLabel="Search services"
          // Screen readers get the stable description, never the word that happens
          // to be on screen at that instant.
          accessibilityHint={placeholder}
          style={{ color: appearance === "fuvay" ? theme.fuvay.surfaces.text : theme.colors.textPrimary, ...theme.typography.body }}
        />
        {showAnimated ? (
          <View
            pointerEvents="none"
            accessibilityElementsHidden
            importantForAccessibility="no-hide-descendants"
            style={{ position: "absolute", left: 0, right: 0, flexDirection: "row" }}
          >
            <Animated.Text style={hintStyle}>{suggestionPrefix}</Animated.Text>
            {/* One line tall and clipped: the outgoing and incoming words are never
                both visible, which is what separates a scroll from a glitch. */}
            <View style={{ flex: 1, height: lineHeight, overflow: "hidden" }}>
              <Animated.View style={{ transform: [{ translateY }] }}>
                {[...items, items[0]].map((word, i) => (
                  // Index-keyed on purpose: this is a positional strip, and the first
                  // word deliberately appears twice, so its name is not a unique key.
                  <Animated.Text key={`${i}-${word}`} numberOfLines={1} style={hintStyle}>
                    {`${word}${suggestionSuffix}`}
                  </Animated.Text>
                ))}
              </Animated.View>
            </View>
          </View>
        ) : null}
      </View>
      {rightAccessory}
    </View>
  );
}
