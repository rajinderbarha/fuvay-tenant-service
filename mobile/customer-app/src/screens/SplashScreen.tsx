import React, { useEffect, useMemo, useRef } from "react";
import { Animated, Easing, Image, View, useWindowDimensions } from "react-native";
import Svg, { Defs, LinearGradient as SvgLinearGradient, RadialGradient, Rect, Stop } from "react-native-svg";

import { AppText } from "../components";
import { useTheme } from "../design-system/theme";
import { buildFuvayTheme } from "../design-system/tokens/fuvay";
import { customerExperienceCopy } from "../content/customerExperience";

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
  const metrics = theme.metrics.splash;
  const copy = customerExperienceCopy.splash;

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

  const logoWidth = Math.min(metrics.logoWidth, Math.round(width * 0.58));
  const logoSource =
    mode === "dark"
      ? require("../../assets/fuvay-wordmark-dark.png")
      : require("../../assets/fuvay-logo.png");

  return (
    <View
      style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}
      accessibilityRole="progressbar"
      accessibilityLabel={copy.accessibilityLabel}
    >
      <Svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none" style={{ position: "absolute", inset: 0 }}>
        <Defs>
          <SvgLinearGradient id="splashBase" x1="78" y1="4" x2="12" y2="100" gradientUnits="userSpaceOnUse">
            {fuvay.surfaces.splashGradient.map((color, index) => <Stop key={color} offset={`${(index / (fuvay.surfaces.splashGradient.length - 1)) * 100}%`} stopColor={color} />)}
          </SvgLinearGradient>
          <RadialGradient id="splashTopGlow" cx="82" cy="3" r="72" gradientUnits="userSpaceOnUse">
            <Stop offset="0" stopColor={fuvay.accents.a2} stopOpacity={mode === "dark" ? 0.16 : 0.11} />
            <Stop offset="1" stopColor={fuvay.accents.a2} stopOpacity="0" />
          </RadialGradient>
          <RadialGradient id="splashLowerGlow" cx="18" cy="72" r="56" gradientUnits="userSpaceOnUse">
            <Stop offset="0" stopColor={fuvay.accents.a2} stopOpacity={mode === "dark" ? 0.12 : 0.09} />
            <Stop offset="1" stopColor={fuvay.accents.a2} stopOpacity="0" />
          </RadialGradient>
        </Defs>
        <Rect width="100" height="100" fill="url(#splashBase)" />
        <Rect width="100" height="100" fill="url(#splashTopGlow)" />
        <Rect width="100" height="100" fill="url(#splashLowerGlow)" />
      </Svg>

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
              style={{ width: logoWidth, height: Math.round(logoWidth / metrics.logoAspectRatio) }}
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
                backgroundColor: fuvay.surfaces.sheen,
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
              width: metrics.brandRuleWidth,
              height: metrics.loadingTrackHeight,
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
              {copy.tagline}
            </AppText>
          </Animated.View>
        </Animated.View>
      </View>

      <View style={{ position: "absolute", left: 34, right: 34, bottom: 46, alignItems: "center", gap: 14 }}>
        <View
          style={{
            width: metrics.loadingTrackWidth,
            height: metrics.loadingTrackHeight,
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
          {copy.loadingLabel}
        </AppText>
      </View>
    </View>
  );
}
