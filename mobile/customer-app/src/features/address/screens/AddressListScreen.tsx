import React, { useState } from "react";
import { View } from "react-native";
import { useNavigation, useRoute, type RouteProp } from "@react-navigation/native";
import { useTranslation } from "react-i18next";
import { ScreenContainer } from "../../../components/layout/ScreenContainer";
import { Stack } from "../../../components/layout/Stack";
import { AppText } from "../../../components/primitives/AppText";
import { AppButton } from "../../../components/primitives/AppButton";
import { AppCard } from "../../../components/primitives/AppCard";
import { AppPressable } from "../../../components/primitives/AppPressable";
import { AppIcon } from "../../../components/primitives/AppIcon";
import { Skeleton } from "../../../components/feedback/Skeleton";
import { EmptyState } from "../../../components/feedback/EmptyState";
import { ErrorState } from "../../../components/feedback/ErrorState";
import { ConfirmationModal } from "../../../components/feedback/ConfirmationModal";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";
import { useAddresses, useDeleteAddress } from "../queries/address-queries";
import { useUpdateDraft } from "../../booking-draft/queries/draft-queries";
import { logger } from "../../../observability/logger";
import type { ValidatedAddress } from "../domain/address-schema";
import type { RootStackParamList } from "../../../navigation/route-types";
import type { AddressId } from "../../../navigation/route-params";

type AddressListRouteProp = RouteProp<RootStackParamList, "AddressSelection">;

/**
 * The real production address list screen (CUSTOMER-L5-07), replacing
 * CUSTOMER-L5-06's dev-only placeholder at the same route. Selecting an
 * address attaches it to the real draft via `PUT .../draft_id`
 * (`address_id`), then navigates to the real serviceability check.
 */
export function AddressListScreen() {
  const { theme } = useAppTheme();
  const { t } = useTranslation("discovery");
  const navigation = useNavigation<any>();
  const route = useRoute<AddressListRouteProp>();
  const { draftId } = route.params;

  const addresses = useAddresses();
  const deleteAddress = useDeleteAddress();
  const updateDraft = useUpdateDraft();
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

  async function handleSelect(address: ValidatedAddress) {
    try {
      await updateDraft.mutateAsync({ draftId, payload: { address_id: address.id } });
      navigation.navigate("ServiceabilityCheck", { draftId, addressId: address.id as AddressId });
    } catch {
      logger.warn("draft_save_conflict", {});
    }
  }

  return (
    <ScreenContainer onRefresh={() => void addresses.refetch()} refreshing={addresses.isRefetching}>
      <Stack gap={5}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
          <AppPressable accessibilityLabel="Go back" onPress={() => navigation.goBack()}>
            <AppIcon name="chevron-back" size="md" color="iconPrimary" />
          </AppPressable>
          <AppText variant="headingLarge" accessibilityRole="header" style={{ flex: 1 }}>
            {t("address.title")}
          </AppText>
        </View>

        {addresses.isLoading ? (
          <Stack gap={3}>
            <Skeleton height={88} />
            <Skeleton height={88} width="90%" />
          </Stack>
        ) : addresses.isError ? (
          <ErrorState title={t("address.loadError")} onRetry={() => void addresses.refetch()} />
        ) : addresses.data && addresses.data.length > 0 ? (
          <Stack gap={3}>
            {addresses.data.map((address) => (
              <AppCard key={address.id} variant="interactive" onPress={() => void handleSelect(address)} accessibilityLabel={address.address_line_1}>
                <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <View style={{ flex: 1, gap: theme.spacing[1] }}>
                    {address.is_default ? (
                      <AppText variant="labelMedium" color="textLink">
                        {t("address.default")}
                      </AppText>
                    ) : null}
                    <AppText variant="labelLarge">{address.address_line_1}</AppText>
                    <AppText variant="bodySmall" color="textSecondary">
                      {[address.city, address.state, address.zipcode].filter(Boolean).join(", ")}
                    </AppText>
                  </View>
                  <View style={{ flexDirection: "row", gap: theme.spacing[3] }}>
                    <AppPressable
                      accessibilityLabel={`${t("address.edit")} ${address.address_line_1}`}
                      onPress={() => navigation.navigate("AddressForm", { draftId, addressId: address.id as AddressId })}
                    >
                      <AppIcon name="settings" size="sm" color="iconSecondary" />
                    </AppPressable>
                    <AppPressable accessibilityLabel={`${t("address.delete")} ${address.address_line_1}`} onPress={() => setPendingDeleteId(address.id)}>
                      <AppIcon name="close-circle" size="sm" color="iconDanger" />
                    </AppPressable>
                  </View>
                </View>
              </AppCard>
            ))}
          </Stack>
        ) : (
          <EmptyState title={t("address.empty")} description={t("address.emptyDescription")} icon="location" />
        )}

        <AppButton
          label={t("address.addNew")}
          onPress={() => navigation.navigate("AddressForm", { draftId })}
          variant="secondary"
          size="large"
          testID="address-add-new-button"
        />
      </Stack>

      <ConfirmationModal
        visible={pendingDeleteId !== null}
        title={t("address.deleteConfirmTitle")}
        description={t("address.deleteConfirmDescription")}
        confirmLabel={t("address.deleteConfirm")}
        cancelLabel={t("address.deleteCancel")}
        destructive
        onConfirm={async () => {
          if (pendingDeleteId) await deleteAddress.mutateAsync(pendingDeleteId);
          setPendingDeleteId(null);
        }}
        onCancel={() => setPendingDeleteId(null)}
      />
    </ScreenContainer>
  );
}
