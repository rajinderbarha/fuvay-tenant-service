import React from "react";
import { View, ScrollView } from "react-native";
import { useNavigation, useRoute, type RouteProp } from "@react-navigation/native";
import { useTranslation } from "react-i18next";
import { SafeAreaView } from "react-native-safe-area-context";
import { AppText } from "../../../components/primitives/AppText";
import { AppButton } from "../../../components/primitives/AppButton";
import { AppPressable } from "../../../components/primitives/AppPressable";
import { AppIcon } from "../../../components/primitives/AppIcon";
import { Stack } from "../../../components/layout/Stack";
import { Skeleton } from "../../../components/feedback/Skeleton";
import { ErrorState } from "../../../components/feedback/ErrorState";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";
import { useServiceDetail } from "../queries/service-detail-queries";
import { evaluateBookingBoundary } from "../domain/booking-boundary";
import { useAuthSession } from "../../auth/hooks/use-auth-session";
import { formatCurrency } from "../../../localization/formatters";
import { getRequestLocale } from "../../../api/request-context";
import { logger } from "../../../observability/logger";
import type { SupportedLocale } from "../../../config/app-config";
import type { RootStackParamList } from "../../../navigation/route-types";

type ServiceDetailsRouteProp = RouteProp<RootStackParamList, "ServiceDetails">;

/**
 * The real production service-detail screen (CUSTOMER-L5-04). Only real
 * backend fields are shown — the offering contract has no images array, no
 * included/excluded items, no preparation instructions, and no supported
 * brands (see CUSTOMER-L5-04-contract-matrix.md), so those sections are
 * simply absent rather than rendered empty or fabricated.
 */
export function ServiceDetailScreen() {
  const { theme } = useAppTheme();
  const { t } = useTranslation("discovery");
  const navigation = useNavigation<any>();
  const route = useRoute<ServiceDetailsRouteProp>();
  const { serviceId, categoryId } = route.params;
  const locale = getRequestLocale() as SupportedLocale;
  const { status } = useAuthSession();

  const detail = useServiceDetail(categoryId, serviceId);
  const boundary = evaluateBookingBoundary({ authenticated: status === "authenticated" });

  function handleBookPress() {
    if (boundary !== "AVAILABLE") return;
    logger.info("service_booking_started", { serviceId, categoryId });
    navigation.navigate("BookingAssistant", { serviceId, categoryId });
  }

  if (detail.isLoading) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[4] }}>
          <Skeleton height={28} width="70%" />
          <Skeleton height={120} />
        </View>
      </SafeAreaView>
    );
  }

  if (detail.isError || !detail.data) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ padding: theme.sizes.screenHorizontalPadding as number }}>
          <ErrorState title={t("service.loadError")} onRetry={() => void detail.refetch()} />
        </View>
      </SafeAreaView>
    );
  }

  const service = detail.data;
  const hasStartingPrice = service.starting_price > 0;
  const requirementChips: string[] = [];
  if (service.required_fields.requires_address) requirementChips.push(t("service.requiresAddress"));
  if (service.required_fields.requires_slot) requirementChips.push(t("service.requiresSlot"));
  if (service.required_fields.requires_brand) requirementChips.push(t("service.requiresBrand"));
  if (service.required_fields.requires_type) requirementChips.push(t("service.requiresType"));
  if (service.required_fields.requires_photo_upload) requirementChips.push(t("service.requiresPhoto"));

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "bottom", "left", "right"]}>
      <ScrollView contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[5], flexGrow: 1 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
          <AppPressable accessibilityLabel="Go back" onPress={() => navigation.goBack()}>
            <AppIcon name="chevron-back" size="md" color="iconPrimary" />
          </AppPressable>
          <AppText variant="headingLarge" accessibilityRole="header" style={{ flex: 1 }}>
            {service.name}
          </AppText>
        </View>

        <AppText variant="bodySmall" color="textSecondary">
          {t("service.categoryContext", { categoryName: service.category.name })}
        </AppText>

        {service.description ? <AppText variant="bodyMedium">{service.description}</AppText> : null}

        {hasStartingPrice ? (
          <Stack gap={1}>
            <AppText variant="titleLarge">{t("category.startingFrom", { price: formatCurrency(service.starting_price, locale) })}</AppText>
            <AppText variant="caption" color="textTertiary">
              {t("category.priceDisclaimer")}
            </AppText>
          </Stack>
        ) : null}

        {requirementChips.length > 0 ? (
          <Stack gap={2}>
            {requirementChips.map((chip) => (
              <View key={chip} style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[2] }}>
                <AppIcon name="information-circle" size="sm" color="iconSecondary" />
                <AppText variant="bodySmall" color="textSecondary">
                  {chip}
                </AppText>
              </View>
            ))}
          </Stack>
        ) : null}

        <AppText variant="bodySmall" color="textTertiary">
          {t("service.providerNote")}
        </AppText>

        <View style={{ flex: 1 }} />

        <AppButton
          label={boundary === "AUTH_REQUIRED" ? t("service.signInToBook") : t("service.bookService")}
          onPress={handleBookPress}
          variant="primary"
          size="large"
          testID="service-detail-book-button"
        />
      </ScrollView>
    </SafeAreaView>
  );
}
