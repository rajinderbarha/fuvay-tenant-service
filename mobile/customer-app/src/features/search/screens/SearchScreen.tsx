import React, { useMemo, useState } from "react";
import { View } from "react-native";
import { useNavigation, useRoute, type RouteProp } from "@react-navigation/native";
import { useTranslation } from "react-i18next";
import { SafeAreaView } from "react-native-safe-area-context";
import { ScreenContainer } from "../../../components/layout/ScreenContainer";
import { Stack } from "../../../components/layout/Stack";
import { Section } from "../../../components/layout/Section";
import { AppText } from "../../../components/primitives/AppText";
import { AppButton } from "../../../components/primitives/AppButton";
import { AppPressable } from "../../../components/primitives/AppPressable";
import { AppIcon } from "../../../components/primitives/AppIcon";
import { AppTextField } from "../../../components/forms/AppTextField";
import { Skeleton } from "../../../components/feedback/Skeleton";
import { ErrorState } from "../../../components/feedback/ErrorState";
import { EmptyState } from "../../../components/feedback/EmptyState";
import { OfflineBanner } from "../../../components/feedback/OfflineBanner";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";
import { useAuthSession } from "../../auth/hooks/use-auth-session";
import { useRecentSearches } from "../hooks/use-recent-searches";
import { useDebouncedValue } from "../hooks/use-debounced-value";
import { useSearchResults } from "../queries/search-queries";
import { normalizeSearchQuery, isSearchableQuery } from "../domain/query-normalization";
import { SearchCategoryResult } from "../components/SearchCategoryResult";
import { SearchServiceResult } from "../components/SearchServiceResult";
import { getRequestLocale } from "../../../api/request-context";
import { logger } from "../../../observability/logger";
import type { SupportedLocale } from "../../../config/app-config";
import type { ValidatedCategorySummary } from "../../home/domain/category-schema";
import type { RootStackParamList } from "../../../navigation/route-types";
import type { CategoryId } from "../../../navigation/route-params";

type SearchRouteProp = RouteProp<RootStackParamList, "Search">;

const DEBOUNCE_MS = 350;

/**
 * The real production search screen (CUSTOMER-L5-04). There is no
 * suggestions endpoint, no popular-searches endpoint, and no backend search
 * history — see CUSTOMER-L5-04-contract-matrix.md — so this screen shows
 * only: a debounced live query against the real `/v1/customer/search`
 * endpoint, and a local, customer-scoped recent-searches list. Neither
 * suggestions nor popular searches are fabricated.
 */
export function SearchScreen() {
  const { theme } = useAppTheme();
  const { t } = useTranslation("discovery");
  const navigation = useNavigation<any>();
  const route = useRoute<SearchRouteProp>();
  const { session } = useAuthSession();
  const locale = getRequestLocale() as SupportedLocale;

  const [rawQuery, setRawQuery] = useState(route.params?.initialQuery ?? "");
  const debouncedRaw = useDebouncedValue(rawQuery, DEBOUNCE_MS);
  const normalized = useMemo(() => normalizeSearchQuery(debouncedRaw), [debouncedRaw]);
  const searchable = isSearchableQuery(normalized);

  const recent = useRecentSearches(session?.userId);
  const results = useSearchResults(normalized, undefined, searchable);

  const hasCommittedThisQuery = React.useRef<string | null>(null);
  React.useEffect(() => {
    if (results.isSuccess && hasCommittedThisQuery.current !== normalized) {
      hasCommittedThisQuery.current = normalized;
      void recent.add(normalized);
      logger.info("search_results_loaded", { queryLength: normalized.length, resultCount: results.data.categories.length + results.data.offerings.length });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only re-run when the committed query or its success state changes.
  }, [results.isSuccess, normalized]);

  function handleCategoryPress(category: ValidatedCategorySummary) {
    navigation.navigate("CategoryDetail", { categoryId: category.id as CategoryId });
  }

  const showRecent = !searchable;
  const totalResultCount = (results.data?.categories.length ?? 0) + (results.data?.offerings.length ?? 0);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "left", "right"]}>
      <ScreenContainer scrollable={!showRecent && results.isSuccess === false}>
        <Stack gap={5}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
            <AppPressable accessibilityLabel="Go back" onPress={() => navigation.goBack()}>
              <AppIcon name="chevron-back" size="md" color="iconPrimary" />
            </AppPressable>
            <View style={{ flex: 1 }}>
              <AppTextField
                label={t("search.placeholder")}
                value={rawQuery}
                onChangeText={setRawQuery}
                autoCapitalize="none"
                returnKeyType="search"
                testID="search-input"
                rightAction={
                  rawQuery.length > 0 ? (
                    <AppPressable accessibilityLabel={t("search.clear")} onPress={() => setRawQuery("")}>
                      <AppIcon name="close" size="sm" color="iconSecondary" />
                    </AppPressable>
                  ) : undefined
                }
              />
            </View>
          </View>

          <OfflineBanner />

          {!searchable && rawQuery.length > 0 ? (
            <AppText variant="caption" color="textTertiary">
              {t("search.minLengthHint")}
            </AppText>
          ) : null}

          {showRecent ? (
            recent.items.length > 0 ? (
              <Section title={t("search.recentTitle")}>
                <View style={{ flexDirection: "row", justifyContent: "flex-end" }}>
                  <AppButton label={t("search.clearRecent")} onPress={() => void recent.clear()} variant="text" size="small" />
                </View>
                <Stack gap={2}>
                  {recent.items.map((term) => (
                    <View key={term} style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
                      <AppPressable style={{ flex: 1 }} onPress={() => setRawQuery(term)} accessibilityLabel={term}>
                        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
                          <AppIcon name="reload" size="sm" color="iconSecondary" />
                          <AppText variant="bodyMedium">{term}</AppText>
                        </View>
                      </AppPressable>
                      <AppPressable accessibilityLabel={`${t("search.removeRecent")} ${term}`} onPress={() => void recent.remove(term)}>
                        <AppIcon name="close" size="sm" color="iconSecondary" />
                      </AppPressable>
                    </View>
                  ))}
                </Stack>
              </Section>
            ) : null
          ) : results.isLoading ? (
            <Stack gap={3}>
              <Skeleton height={64} />
              <Skeleton height={64} width="85%" />
            </Stack>
          ) : results.isError ? (
            <ErrorState title={t("search.loadError")} onRetry={() => void results.refetch()} />
          ) : results.data ? (
            totalResultCount === 0 ? (
              <EmptyState
                title={t("search.noResultsTitle", { query: normalized })}
                description={t("search.noResultsDescription")}
                icon="search"
                primaryAction={{ label: t("search.browseCategoriesAction"), onPress: () => navigation.navigate("Home") }}
              />
            ) : (
              <Stack gap={5}>
                {results.data.categories.length > 0 ? (
                  <Section title={t("search.categoriesTitle")}>
                    {results.data.categories.map((category) => (
                      <SearchCategoryResult key={category.id} category={category} onPress={handleCategoryPress} />
                    ))}
                  </Section>
                ) : null}
                {results.data.offerings.length > 0 ? (
                  <Section title={t("search.servicesTitle")}>
                    {results.data.offerings.map((offering) => (
                      <SearchServiceResult key={offering.id} offering={offering} locale={locale} />
                    ))}
                  </Section>
                ) : null}
              </Stack>
            )
          ) : null}
        </Stack>
      </ScreenContainer>
    </SafeAreaView>
  );
}
