import React, { useEffect, useState } from "react";
import { View, ScrollView } from "react-native";
import { useNavigation, useRoute, type RouteProp } from "@react-navigation/native";
import { useTranslation } from "react-i18next";
import { SafeAreaView } from "react-native-safe-area-context";
import { AppText } from "../../../components/primitives/AppText";
import { AppButton } from "../../../components/primitives/AppButton";
import { AppPressable } from "../../../components/primitives/AppPressable";
import { AppIcon } from "../../../components/primitives/AppIcon";
import { AppTextField } from "../../../components/forms/AppTextField";
import { Skeleton } from "../../../components/feedback/Skeleton";
import { ErrorState } from "../../../components/feedback/ErrorState";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";
import { useCheckServiceability, useUpdateDraft } from "../queries/draft-queries";
import { sanitizeAddressText } from "../../address/domain/address-form-validation";
import { logger } from "../../../observability/logger";
import type { RootStackParamList } from "../../../navigation/route-types";

type ServiceabilityRouteProp = RouteProp<RootStackParamList, "ServiceabilityCheck">;

/**
 * The real production serviceability screen (CUSTOMER-L5-07). Calls the
 * real, ID-space-correct draft serviceability check
 * (`HomeServiceServiceabilityService.check`) — never calculates
 * serviceability client-side. There is no real SLA-options concept to
 * select from (see contract-matrix.md/known-gaps.md) — only the real,
 * unvalidated `preferred_date`/`preferred_time_window` draft fields are
 * collected here.
 */
export function ServiceabilityScreen() {
  const { theme } = useAppTheme();
  const { t } = useTranslation("discovery");
  const navigation = useNavigation<any>();
  const route = useRoute<ServiceabilityRouteProp>();
  const { draftId } = route.params;

  const checkServiceability = useCheckServiceability();
  const updateDraft = useUpdateDraft();
  const [preferredWindow, setPreferredWindow] = useState("");
  const hasChecked = checkServiceability.isSuccess || checkServiceability.isError;

  useEffect(() => {
    if (!hasChecked && !checkServiceability.isPending) {
      checkServiceability.mutate(draftId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- runs once on mount only.
  }, []);

  if (checkServiceability.isPending || (!hasChecked && !checkServiceability.isIdle)) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ flex: 1, padding: theme.sizes.screenHorizontalPadding as number, justifyContent: "center", gap: theme.spacing[4] }}>
          <Skeleton height={28} width="70%" />
          <AppText variant="bodyMedium" color="textSecondary" align="center">
            {t("serviceability.checking")}
          </AppText>
        </View>
      </SafeAreaView>
    );
  }

  if (checkServiceability.isError) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ padding: theme.sizes.screenHorizontalPadding as number }}>
          <ErrorState title={t("serviceability.loadError")} onRetry={() => checkServiceability.mutate(draftId)} />
        </View>
      </SafeAreaView>
    );
  }

  const result = checkServiceability.data;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "bottom", "left", "right"]}>
      <ScrollView contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[5], flexGrow: 1 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
          <AppPressable accessibilityLabel="Go back" onPress={() => navigation.goBack()}>
            <AppIcon name="chevron-back" size="md" color="iconPrimary" />
          </AppPressable>
          <AppText variant="headingLarge" accessibilityRole="header" style={{ flex: 1 }}>
            {t("serviceability.title")}
          </AppText>
        </View>

        {result?.serviceable ? (
          <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
            <AppIcon name="checkmark-circle" size="lg" color="iconSuccess" />
            <View style={{ flex: 1 }}>
              <AppText variant="titleLarge">{t("serviceability.availableTitle")}</AppText>
              <AppText variant="bodySmall" color="textSecondary">
                {result.message}
              </AppText>
            </View>
          </View>
        ) : (
          <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
            <AppIcon name="alert-circle" size="lg" color="iconWarning" />
            <View style={{ flex: 1 }}>
              <AppText variant="titleLarge">{t("serviceability.unavailableTitle")}</AppText>
              <AppText variant="bodySmall" color="textSecondary">
                {result?.message}
              </AppText>
            </View>
          </View>
        )}

        {result?.serviceable ? (
          <View style={{ gap: theme.spacing[4] }}>
            <AppTextField
              label={t("serviceability.preferredWindowLabel")}
              value={preferredWindow}
              onChangeText={(v) => setPreferredWindow(sanitizeAddressText(v, 50))}
              placeholder={t("serviceability.preferredWindowPlaceholder")}
              helperText={t("serviceability.preferredWindowHelper")}
              required={false}
            />
          </View>
        ) : null}

        <View style={{ flex: 1 }} />

        {result?.serviceable ? (
          <AppButton
            label={t("serviceability.continue")}
            onPress={async () => {
              if (preferredWindow.trim()) {
                await updateDraft.mutateAsync({ draftId, payload: { preferred_time_window: preferredWindow.trim() } });
              }
              logger.info("next_available_accepted", {});
              navigation.navigate("ProviderPreview", { draftId });
            }}
            variant="primary"
            size="large"
            testID="serviceability-continue-button"
          />
        ) : (
          <AppButton
            label={t("serviceability.changeAddress")}
            onPress={() => navigation.navigate("AddressSelection", { draftId })}
            variant="primary"
            size="large"
          />
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
