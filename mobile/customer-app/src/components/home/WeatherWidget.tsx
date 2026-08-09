import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon, IconProps } from "../Icon";
import { HomeWeather } from "../../domain/customerHome";

export interface WeatherWidgetProps {
  weather: HomeWeather | null;
  /** The city it applies to, so the reading is not floating free of a place. */
  city: string | null;
  /** Seasonal wording from the backend ("Monsoon picks"), which explains why the
   * services below are ordered the way they are. */
  seasonLabel?: string | null;
}

/**
 * Today's weather, and why the screen below is ordered the way it is.
 *
 * Renders NOTHING without a reading. There is no placeholder temperature, no "--°",
 * and no cheerful default: this data exists so a customer understands why we are
 * suggesting drainage work in July and hot water in December, and a made-up number
 * would undermine every real one next to it. A deployment with no weather source
 * simply has no widget.
 *
 * Deliberately not a forecast and not a warning. Per-visit weather risk belongs on
 * the booking, next to the slot it threatens -- a scary line on Home about a job
 * three days away is anxiety with nothing to act on.
 */
export function WeatherWidget({ weather, city, seasonLabel }: WeatherWidgetProps) {
  const { theme } = useTheme();
  if (!weather) return null;

  const glyph = describe(weather);

  return (
    <View
      style={{
        flexDirection: "row", alignItems: "center", gap: theme.spacing.sm,
        paddingHorizontal: theme.spacing.base, paddingVertical: theme.spacing.sm,
        borderRadius: theme.radiusUsage.card,
        backgroundColor: theme.colors.surfaceSecondary,
      }}
      accessibilityLabel={
        `${Math.round(weather.temperatureC)} degrees${city ? ` in ${city}` : ""}`
        + `${weather.condition ? `, ${weather.condition}` : ""}`
      }
    >
      <View
        style={{
          width: 36, height: 36, borderRadius: theme.radiusUsage.input,
          alignItems: "center", justifyContent: "center",
          backgroundColor: `${glyph.tint}1F`,
        }}
      >
        <Icon name={glyph.icon} size="standard" color={glyph.tint} decorative />
      </View>

      <View style={{ flex: 1, minWidth: 0 }}>
        <View style={{ flexDirection: "row", alignItems: "baseline", gap: theme.spacing.xxs }}>
          <AppText variant="bodyStrong">{`${Math.round(weather.temperatureC)}°C`}</AppText>
          {/* The provider's own words for the sky, not ours -- we do not restate a
              measurement we did not take. */}
          {weather.condition ? (
            <AppText variant="caption" color="secondary" numberOfLines={1}>{weather.condition}</AppText>
          ) : null}
        </View>
        {city || seasonLabel ? (
          <AppText variant="caption" color="tertiary" numberOfLines={1}>
            {[city, seasonLabel].filter(Boolean).join(" · ")}
          </AppText>
        ) : null}
      </View>

      {/* Rain is called out only when there is enough of it to matter to someone
          deciding whether today is a good day for a home visit. */}
      {weather.rainMm >= 1 ? (
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}>
          <Icon name="water-outline" size="compact" color={theme.colors.brandPrimaryStrong} decorative />
          <AppText variant="caption" color="secondary">{`${weather.rainMm} mm`}</AppText>
        </View>
      ) : null}
    </View>
  );
}

/** Icon and tint for the reading. Derived from the MEASUREMENTS first and the
 * provider's wording second, because the numbers are comparable across providers
 * and the wording is not. */
function describe(weather: HomeWeather): { icon: IconProps["name"]; tint: string } {
  const condition = (weather.condition || "").toLowerCase();
  if (weather.rainMm >= 1 || /rain|drizzle|shower|thunder/.test(condition)) {
    return { icon: "rainy-outline", tint: "#2563EB" };
  }
  if (weather.temperatureC >= 38) return { icon: "sunny-outline", tint: "#DC2626" };
  if (weather.temperatureC <= 12) return { icon: "snow-outline", tint: "#0891B2" };
  if (/cloud|overcast|mist|fog|haze/.test(condition)) {
    return { icon: "cloud-outline", tint: "#64748B" };
  }
  return { icon: "sunny-outline", tint: "#D97706" };
}
