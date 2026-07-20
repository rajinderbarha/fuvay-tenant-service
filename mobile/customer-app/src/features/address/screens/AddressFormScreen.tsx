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
import { AppSwitch } from "../../../components/forms/AppSwitch";
import { Skeleton } from "../../../components/feedback/Skeleton";
import { useAppTheme } from "../../../design-system/themes/use-app-theme";
import { useAddresses, useCreateAddress, useUpdateAddress } from "../queries/address-queries";
import { useCurrentLocation } from "../hooks/use-current-location";
import { sanitizeAddressText, validateAddressForm, isAddressFormValid, type AddressFormValues } from "../domain/address-form-validation";
import { toastService } from "../../../components/feedback/toast-service";
import type { RootStackParamList } from "../../../navigation/route-types";

type AddressFormRouteProp = RouteProp<RootStackParamList, "AddressForm">;

const EMPTY_FORM: AddressFormValues = {
  name: "",
  phone: "",
  addressLine1: "",
  addressLine2: "",
  landmark: "",
  city: "",
  district: "",
  state: "",
  zipcode: "",
};

/** The real production address create/edit screen (CUSTOMER-L5-07). */
export function AddressFormScreen() {
  const { theme } = useAppTheme();
  const { t } = useTranslation("discovery");
  const navigation = useNavigation<any>();
  const route = useRoute<AddressFormRouteProp>();
  const { draftId, addressId } = route.params;
  const isEditing = Boolean(addressId);

  const addresses = useAddresses();
  const createAddress = useCreateAddress();
  const updateAddress = useUpdateAddress();
  const { resolveCurrentLocation } = useCurrentLocation();

  const [values, setValues] = useState<AddressFormValues>(EMPTY_FORM);
  const [isDefault, setIsDefault] = useState(false);
  const [coords, setCoords] = useState<{ latitude: number; longitude: number } | null>(null);
  const [locationNotice, setLocationNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!isEditing || !addresses.data) return;
    const existing = addresses.data.find((a) => a.id === addressId);
    if (!existing) return;
    setValues({
      name: existing.name ?? "",
      phone: existing.phone ?? "",
      addressLine1: existing.address_line_1,
      addressLine2: existing.address_line_2 ?? "",
      landmark: existing.landmark ?? "",
      city: existing.city,
      district: existing.district ?? "",
      state: existing.state,
      zipcode: existing.zipcode,
    });
    setIsDefault(existing.is_default);
  }, [isEditing, addressId, addresses.data]);

  function setField<K extends keyof AddressFormValues>(key: K, raw: string) {
    setValues((prev) => ({ ...prev, [key]: sanitizeAddressText(raw, 300) }));
  }

  async function handleUseCurrentLocation() {
    const result = await resolveCurrentLocation();
    if (result.outcome === "permission_denied") {
      setLocationNotice(t("addressForm.permissionDenied"));
      return;
    }
    if (result.outcome === "unavailable") {
      setLocationNotice(t("addressForm.locationUnavailable"));
      return;
    }
    setCoords({ latitude: result.prefill.latitude, longitude: result.prefill.longitude });
    setValues((prev) => ({
      ...prev,
      addressLine1: prev.addressLine1 || result.prefill.addressLine1,
      city: result.prefill.city || prev.city,
      district: result.prefill.district || prev.district,
      state: result.prefill.state || prev.state,
      zipcode: result.prefill.zipcode || prev.zipcode,
    }));
    setLocationNotice(t("addressForm.currentLocationFilled"));
  }

  const errors = validateAddressForm(values);
  const canSave = isAddressFormValid(errors);
  const isSaving = createAddress.isPending || updateAddress.isPending;

  async function handleSave() {
    if (!canSave) return;
    const payload = {
      name: values.name || undefined,
      phone: values.phone || undefined,
      address_line_1: values.addressLine1,
      address_line_2: values.addressLine2 || undefined,
      landmark: values.landmark || undefined,
      city: values.city,
      district: values.district || undefined,
      state: values.state,
      zipcode: values.zipcode,
      latitude: coords?.latitude,
      longitude: coords?.longitude,
      is_default: isDefault,
    };
    try {
      if (isEditing && addressId) {
        await updateAddress.mutateAsync({ addressId, payload });
      } else {
        await createAddress.mutateAsync(payload);
      }
      navigation.navigate("AddressSelection", { draftId });
    } catch {
      toastService.info(t("addressForm.saveFailed"));
    }
  }

  if (isEditing && addresses.isLoading) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }}>
        <View style={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[4] }}>
          <Skeleton height={28} width="60%" />
          <Skeleton height={200} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.colors.backgroundPrimary }} edges={["top", "bottom", "left", "right"]}>
      <ScrollView contentContainerStyle={{ padding: theme.sizes.screenHorizontalPadding as number, gap: theme.spacing[4], flexGrow: 1 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing[3] }}>
          <AppPressable accessibilityLabel="Go back" onPress={() => navigation.goBack()}>
            <AppIcon name="chevron-back" size="md" color="iconPrimary" />
          </AppPressable>
          <AppText variant="headingLarge" accessibilityRole="header" style={{ flex: 1 }}>
            {isEditing ? t("addressForm.titleEdit") : t("addressForm.titleAdd")}
          </AppText>
        </View>

        <AppButton label={t("address.useCurrentLocation")} onPress={() => void handleUseCurrentLocation()} variant="secondary" size="medium" />
        {locationNotice ? (
          <AppText variant="caption" color="textTertiary">
            {locationNotice}
          </AppText>
        ) : null}

        <AppTextField label={t("addressForm.name")} value={values.name} onChangeText={(v) => setField("name", v)} required={false} />
        <AppTextField
          label={t("addressForm.phone")}
          value={values.phone}
          onChangeText={(v) => setField("phone", v)}
          keyboardType="phone-pad"
          required={false}
        />
        <AppTextField
          label={t("addressForm.addressLine1")}
          value={values.addressLine1}
          onChangeText={(v) => setField("addressLine1", v)}
          required
          errorText={errors.addressLine1 ? t("addressForm.required") : undefined}
        />
        <AppTextField label={t("addressForm.addressLine2")} value={values.addressLine2} onChangeText={(v) => setField("addressLine2", v)} required={false} />
        <AppTextField label={t("addressForm.landmark")} value={values.landmark} onChangeText={(v) => setField("landmark", v)} required={false} />
        <AppTextField
          label={t("addressForm.city")}
          value={values.city}
          onChangeText={(v) => setField("city", v)}
          required
          errorText={errors.city ? t("addressForm.required") : undefined}
        />
        <AppTextField label={t("addressForm.district")} value={values.district} onChangeText={(v) => setField("district", v)} required={false} />
        <AppTextField
          label={t("addressForm.state")}
          value={values.state}
          onChangeText={(v) => setField("state", v)}
          required
          errorText={errors.state ? t("addressForm.required") : undefined}
        />
        <AppTextField
          label={t("addressForm.zipcode")}
          value={values.zipcode}
          onChangeText={(v) => setField("zipcode", v)}
          keyboardType="number-pad"
          required
          errorText={errors.zipcode ? t("addressForm.required") : undefined}
        />

        <AppSwitch value={isDefault} onValueChange={setIsDefault} label={t("addressForm.setAsDefault")} />

        <View style={{ flex: 1 }} />

        <AppButton
          label={isSaving ? t("addressForm.saving") : t("addressForm.save")}
          onPress={() => void handleSave()}
          variant="primary"
          size="large"
          disabled={!canSave || isSaving}
          loading={isSaving}
          testID="address-form-save-button"
        />
      </ScrollView>
    </SafeAreaView>
  );
}
