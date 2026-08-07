import React from "react";
import { View, Pressable, Image, ActivityIndicator } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";
import { SearchResult } from "../../domain/customerSearch";
import { resolveCategoryIcon } from "../../domain/categoryIcon";
import { resolveMediaUrl } from "../../domain/mediaUrl";
import { classifyRawAmount } from "../../domain/servicePricing";
import { formatMoney } from "../../domain/money";

export interface SearchResultsListProps {
  query: string;
  isPending: boolean;
  isError: boolean;
  results: SearchResult[];
  /** Only ever called for a result that is bookable at this ZIP. */
  onPressCategory: (categoryId: string) => void;
}

function priceLabel(amount: number | null): string | null {
  const state = classifyRawAmount(amount != null ? Math.round(amount * 100) : null);
  return state.kind === "valid" ? formatMoney(state.amount) : null;
}

/**
 * Results for the Home search box.
 *
 * The search endpoint is NOT ZIP-aware, so a match can name something the
 * customer cannot book where they are. Rather than hiding those (which makes
 * search look broken -- "I know you offer plumbing, why did it find nothing")
 * or offering them as normal (which dead-ends several steps into booking at
 * "no provider available"), they are listed and plainly marked unavailable,
 * and are not tappable.
 */
export function SearchResultsList({ query, isPending, isError, results, onPressCategory }: SearchResultsListProps) {
  const { theme } = useTheme();

  if (isPending) {
    return (
      <View style={{ paddingVertical: theme.spacing.xl, alignItems: "center" }}>
        <ActivityIndicator color={theme.colors.brandPrimary} />
      </View>
    );
  }
  if (isError) {
    return (
      <AppText variant="bodySmall" color="secondary">
        We couldn&apos;t search right now. Please try again.
      </AppText>
    );
  }
  if (results.length === 0) {
    return (
      <AppText variant="bodySmall" color="secondary">{`No services match "${query}".`}</AppText>
    );
  }

  return (
    <View style={{ gap: theme.spacing.sm }}>
      {results.map(r => {
        const key = r.kind === "category" ? `c:${r.categoryId}` : `o:${r.offeringId}`;
        const price = r.kind === "offering" ? priceLabel(r.startingPrice) : null;
        const artwork = r.kind === "category" ? resolveMediaUrl(r.iconUrl) : null;
        const targetCategoryId = r.kind === "category" ? String(r.categoryId) : (r.categoryId ? String(r.categoryId) : null);
        const tappable = r.bookableHere && targetCategoryId !== null;

        return (
          <Pressable
            key={key}
            disabled={!tappable}
            onPress={tappable ? () => onPressCategory(targetCategoryId as string) : undefined}
            accessibilityRole={tappable ? "button" : "text"}
            accessibilityLabel={
              tappable ? r.name : `${r.name}, not available at your location`
            }
            style={({ pressed }) => ({
              flexDirection: "row", alignItems: "center", gap: theme.spacing.base,
              padding: theme.spacing.base, borderRadius: theme.radiusUsage.card,
              backgroundColor: theme.colors.surfaceDefault,
              borderWidth: 1,
              borderColor: pressed && tappable ? theme.colors.brandPrimary : theme.colors.borderSubtle,
              opacity: tappable ? (pressed ? 0.9 : 1) : 0.55,
            })}
          >
            <View
              style={{
                width: 44, height: 44, borderRadius: theme.radiusUsage.input,
                alignItems: "center", justifyContent: "center", overflow: "hidden", flexShrink: 0,
                backgroundColor: artwork ? "transparent" : theme.colors.brandPrimaryMuted,
              }}
            >
              {artwork ? (
                <Image source={{ uri: artwork }} style={{ width: "100%", height: "100%" }} resizeMode="contain" />
              ) : (
                <Icon
                  name={r.kind === "category" ? resolveCategoryIcon(r.slug) : "pricetag-outline"}
                  size="standard"
                  color={theme.colors.brandPrimaryStrong}
                  decorative
                />
              )}
            </View>

            <View style={{ flex: 1, minWidth: 0 }}>
              <AppText variant="bodyStrong" numberOfLines={1}>{r.name}</AppText>
              {r.description ? (
                <AppText variant="caption" color="tertiary" numberOfLines={1} style={{ marginTop: 2 }}>
                  {r.description}
                </AppText>
              ) : null}
              {!r.bookableHere ? (
                <AppText variant="caption" color="tertiary" style={{ marginTop: 2 }}>
                  Not available at your location
                </AppText>
              ) : price ? (
                <View style={{ flexDirection: "row", alignItems: "baseline", gap: 4, marginTop: 2 }}>
                  <AppText variant="caption" color="tertiary">Starting at</AppText>
                  <AppText variant="bodySmall" style={{ color: theme.colors.brandPrimaryStrong, fontWeight: "700" }}>
                    {price}
                  </AppText>
                </View>
              ) : null}
            </View>

            {tappable ? (
              <Icon name="chevron-forward" size="compact" color={theme.colors.iconDefault} decorative />
            ) : null}
          </Pressable>
        );
      })}
    </View>
  );
}
