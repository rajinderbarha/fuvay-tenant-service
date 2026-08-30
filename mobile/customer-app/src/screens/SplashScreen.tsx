import React, { useEffect, useMemo, useRef } from "react";
import { Animated, Easing, Image, View, useWindowDimensions } from "react-native";
import { LinearGradient } from "expo-linear-gradient";

import { AppText } from "../components";
import { useTheme } from "../design-system/theme";
import { buildFuvayTheme } from "../design-system/tokens/fuvay";

/**
 * Fuvay v2 splash.
 *
 * The canvas builds this from eight CSS keyframes; they collapse to four
 * Animated values here because several of them are the same motion applied
 * to different properties, and running one driver per property would mean
 * four timers where one will do:
 *
 *   brandLift + brandWipe  -> `brand`   (logo rises and reveals)
 *   sheenSweep             -> `sheen`   (highlight sweeps across the mark)
 *   ruleGrow + letterSettle-> `tagline` (rule scales out, tagline settles)
 *   trackFill              -> `track`   (loading bar fills)
 *
 * `ambientDrift` (the slow background glow) is deliberately dropped: it is a
 * 9s infinite loop on a blurred radial that RN cannot render cheaply without
 * a real blur, and an always-running driver on a screen shown for ~2s costs
 * battery for something nobody sees finish.
 *
 * Every animation uses `useNativeDriver` so the sequence stays smooth while
 * the JS thread is busy doing the actual bootstrap work this screen covers.
 */
export function SplashScreen() {
  const { theme, mode } = useTheme();
  const fuvay = useMemo(() => buildFuvayTheme(mode === "dark"), [mode]);
  const { width } = useWindowDimensions();

  const brand = useRef(new Animated.Value(0)).current;
  const sheen = useRef(new Animated.Value(0)).current;
  const tagline = useRef(new Animated.Value(0)).current;
  const track = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // Timings mirror the canvas: brand 1.1s, sheen at 0.75s, tagline at
    // 0.55s, track fill 2.6s starting at 1.2s.
    const sequence = Animated.parallel([
      Animated.timing(brand, {
        toValue: 1,
        duration: 1100,
        easing: Easing.bezier(0.16, 0.84, 0.24, 1),
        useNativeDriver: true,
      }),
      Animated.sequence([
        Animated.delay(750),
        Animated.timing(sheen, {
          toValue: 1,
          duration: 1500,
          easing: Easing.bezier(0.4, 0, 0.2, 1),
          useNativeDriver: true,
        }),
      ]),
      Animated.sequence([
        Animated.delay(550),
        Animated.timing(tagline, {
          toValue: 1,
          duration: 900,
          easing: Easing.bezier(0.16, 0.84, 0.24, 1),
          useNativeDriver: true,
        }),
      ]),
      Animated.sequence([
        Animated.delay(1200),
        Animated.timing(track, {
          toValue: 1,
          duration: 2600,
          easing: Easing.bezier(0.35, 0, 0.2, 1),
          useNativeDriver: true,
        }),
      ]),
    ]);
    sequence.start();
    return () => sequence.stop();
  }, [brand, sheen, tagline, track]);

  const logoWidth = Math.min(216, Math.round(width * 0.58));
  const logoSource =
    mode === "dark"
      ? require("../../assets/fuvay-logo-native.png")
      : require("../../assets/fuvay-logo.png");

  return (
    <View
      style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}
      accessibilityRole="progressbar"
      accessibilityLabel="Loading Fuvay"
    >
      <LinearGradient
        colors={fuvay.surfaces.splashGradient}
        // The canvas anchors this radial at 78% 6%; a linear gradient on the
        // same diagonal is the closest RN equivalent without shipping an SVG
        // radial for a screen that is visible for two seconds.
        start={{ x: 0.78, y: 0.06 }}
        end={{ x: 0.1, y: 1 }}
        style={{ position: "absolute", inset: 0 }}
      />

      {/* Ambient glows. Static rather than drifting -- see the header note. */}
      <View
        style={{
          position: "absolute",
          right: -110,
          top: -120,
          width: 320,
          height: 320,
          borderRadius: 160,
          backgroundColor: fuvay.surfaces.glowTint,
        }}
      />
      <View
        style={{
          position: "absolute",
          left: -90,
          bottom: 130,
          width: 260,
          height: 260,
          borderRadius: 130,
          backgroundColor: fuvay.surfaces.glowTint,
        }}
      />

      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", paddingHorizontal: 34 }}>
        <Animated.View
          style={{
            alignItems: "center",
            gap: 20,
            opacity: brand,
            transform: [
              {
                translateY: brand.interpolate({
                  inputRange: [0, 1],
                  outputRange: [22, 0],
                }),
              },
            ],
          }}
        >
          <View style={{ overflow: "hidden" }}>
            <Image
              source={logoSource}
              resizeMode="contain"
              style={{ width: logoWidth, height: Math.round(logoWidth / 3.25) }}
              accessibilityRole="image"
              accessibilityLabel="Fuvay"
              accessibilityIgnoresInvertColors
            />
            {/* Sheen: a narrow translucent band swept across the wordmark. */}
            <Animated.View
              pointerEvents="none"
              style={{
                position: "absolute",
                top: 0,
                bottom: 0,
                width: 42,
                backgroundColor: fuvay.isDark
                  ? "rgba(255,255,255,0.28)"
                  : "rgba(255,255,255,0.75)",
                opacity: sheen.interpolate({
                  inputRange: [0, 0.15, 0.85, 1],
                  outputRange: [0, 1, 1, 0],
                }),
                transform: [
                  {
                    translateX: sheen.interpolate({
                      inputRange: [0, 1],
                      outputRange: [-42, logoWidth + 42],
                    }),
                  },
                ],
              }}
            />
          </View>

          <Animated.View
            style={{
              width: 46,
              height: 2,
              backgroundColor: fuvay.accents.a2,
              transform: [{ scaleX: tagline }],
            }}
          />

          <Animated.View
            style={{
              opacity: tagline,
              transform: [
                {
                  translateY: tagline.interpolate({
                    inputRange: [0, 1],
                    outputRange: [8, 0],
                  }),
                },
              ],
            }}
          >
            <AppText
              variant="metaLabel"
              style={{ color: theme.colors.textSecondary, textAlign: "center" }}
            >
              HOME SERVICES, DONE RIGHT
            </AppText>
          </Animated.View>
        </Animated.View>
      </View>

      <View style={{ position: "absolute", left: 34, right: 34, bottom: 46, alignItems: "center", gap: 14 }}>
        <View
          style={{
            width: 120,
            height: 2,
            borderRadius: 2,
            backgroundColor: theme.colors.divider,
            overflow: "hidden",
          }}
        >
          <Animated.View
            style={{
              width: "100%",
              height: "100%",
              borderRadius: 2,
              backgroundColor: fuvay.accents.a2,
              // scaleX from the left edge, so the bar fills rather than grows
              // from its centre.
              transform: [{ translateX: -60 }, { scaleX: track }, { translateX: 60 }],
            }}
          />
        </View>
        <AppText variant="metaLabelWide" style={{ color: theme.colors.textTertiary }}>
          LOADING YOUR HOME
        </AppText>
      </View>
    </View>
  );
}
