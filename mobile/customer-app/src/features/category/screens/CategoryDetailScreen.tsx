import React, { useMemo } from "react";
import { View, FlatList } from "react-native";
import { useNavigation, useRoute, type RouteProp } from "@react-navigation/native";
import { useTranslation } from "react-i18next";
import { SafeAreaView } from "react-native-safe-area-context";
import { AppText } from "../../../components/primitives/AppText";
import { AppPressable } from "../../../components/primitives/AppPressable";
import { AppIcon } from "../../../components/primitives/AppIcon";
import { Stack } from "../../../components/layout/Stack";
import { Skeleton } from "../../../components/feedback/Skeleton";
import { EmptyState } from "../../../components/feedback/EmptyState";
import { ErrorState } from "../../../components/feedback/ErrorState";
import { OfflineBanner } from "../../../components/feedback/OfflineBanner";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";
import { useCategoryDetail, useCategoryOfferings } from "../queries/category-queries";
import { ServiceListItem } from "../components/ServiceListItem";
import { getRequestLocale } from "../../../api/request-context";
import type { SupportedLocale } from "../../../config/app-config";
import type { ValidatedOfferingSummary } from "../domain/offering-schema";
import type { RootStackParamList } from "../../../navigation/route-types";
import type { CategoryId, ServiceId } from "../../../navigation/route-params";

type CategoryDetailRouteProp = RouteProp<RootStackParamList, "CategoryDetail">;

/**
 * The real production category-detail screen (CUSTOMER-L5-04). There is no
 * subcategory/parent-category concept anywhere in the backend catalogue —
 * see CUSTOMER-L5-04-contract-matrix.md — so this screen shows exactly the
 * category's own metadata plus its flat service list, never a fabricated
 * hierarchy.
 */
export function CategoryDetailScreen() {
  const { theme } = useAppTheme();
  const { t } = useTranslation("discovery");
  const navigation = useNavigation<any>();
  const route = useRoute<CategoryDetailRouteProp>();
  const categoryId = route.params.categoryId;
  const locale = getRequestLocale() as SupportedLocale;

  const detail = useCategoryDetail(categoryId);
  const offerings = useCategoryOfferings(categoryId);

  const flatOfferings = useMemo<ValidatedOfferingSummary[]>(() => offerings.data?.pages.flatMap((page) => page.items) ?? [], [offerings.data]);

  function handleServicePress(offering: ValidatedOfferingSummary) {
    navigation.navigate("ServiceDetails", { serviceId: offering.id as ServiceId, categoryId: categoryId as CategoryId });
  }

  if (detail.isLoading) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[4] }}>
          <Skeleton height={28} width="60%" />
          <Skeleton height={80} />
        </View>
      </SafeAreaView>
    );
  }

  if (detail.isError || !detail.data) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ padding: theme.sizes.screenHorizontalPadding as number }}>
          <ErrorState title={t("category.loadError")} description={t("category.loadErrorDescription")} onRetry={() => void detail.refetch()} />
        </View>
      </SafeAreaView>
    );
  }

  const category = detail.data;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "bottom", "left", "right"]}>
      <FlatList
        data={flatOfferings}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[3] }}
        renderItem={({ item }) => <ServiceListItem offering={item} locale={locale} onPress={handleServicePress} />}
        ListHeaderComponent={
          <Stack gap={4} style={{ marginBottom: theme.spacing[6] }}>
            <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
              <AppPressable accessibilityLabel="Go back" onPress={() => navigation.goBack()}>
                <AppIcon name="chevron-back" size="md" color="iconPrimary" />
              </AppPressable>
              <AppText variant="headingLarge" accessibilityRole="header" style={{ flex: 1 }}>
                {category.name}
              </AppText>
            </View>
            {category.description ? (
              <AppText variant="bodyMedium" color="textSecondary">
                {category.description}
              </AppText>
            ) : null}
            <OfflineBanner />
            <AppText variant="titleSmall" color="textSecondary" style={{ textTransform: "uppercase", marginTop: theme.spacing[2] }}>
              {t("category.servicesSectionTitle")}
            </AppText>
          </Stack>
        }
        ListEmptyComponent={
          offerings.isLoading ? (
            <Stack gap={4}>
              <Skeleton height={72} />
              <Skeleton height={72} width="90%" />
            </Stack>
          ) : offerings.isError ? (
            <ErrorState title={t("category.servicesLoadError")} onRetry={() => void offerings.refetch()} />
          ) : (
            <EmptyState title={t("category.noServices")} description={t("category.noServicesDescription")} icon="list" />
          )
        }
        ListFooterComponent={
          offerings.isFetchingNextPage ? (
            <View style={{ paddingVertical: theme.spacing[4] }}>
              <Skeleton height={72} />
            </View>
          ) : null
        }
        onEndReachedThreshold={0.4}
        onEndReached={() => {
          if (offerings.hasNextPage && !offerings.isFetchingNextPage) void offerings.fetchNextPage();
        }}
        refreshing={detail.isRefetching || offerings.isRefetching}
        onRefresh={() => {
          void detail.refetch();
          void offerings.refetch();
        }}
      />
    </SafeAreaView>
  );
}
