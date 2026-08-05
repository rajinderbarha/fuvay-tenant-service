import React, { useEffect, useState } from "react";
import { View, Alert } from "react-native";
import { useNavigation, useRoute, RouteProp } from "@react-navigation/native";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { AppText } from "../../components/AppText";
import { LoadingState } from "../../components/LoadingState";
import { ErrorState } from "../../components/States";
import { AddressFormHeader } from "../../components/address-form/AddressFormHeader";
import { AddressAvailabilityInfo } from "../../components/address-form/AddressAvailabilityInfo";
import { AddressLabelSelector } from "../../components/address-form/AddressLabelSelector";
import { AddressFormFields } from "../../components/address-form/AddressFormFields";
import { DefaultAddressToggle } from "../../components/address-form/DefaultAddressToggle";
import { AddressHistoricalNote } from "../../components/address-form/AddressHistoricalNote";
import { AddressFormFooter } from "../../components/address-form/AddressFormFooter";
import { useCustomerAddressesQuery } from "../../api/customerAddresses/useCustomerAddressesQuery";
import { useCustomerAddressDetailQuery } from "../../api/customerAddresses/useCustomerAddressDetailQuery";
import { useCreateAddressMutation } from "../../api/customerAddresses/useCreateAddressMutation";
import { useUpdateAddressMutation } from "../../api/customerAddresses/useUpdateAddressMutation";
import {
  AddressFormState, AddressFormErrors, validateAddressForm,
  buildAddressCreatePayload, buildAddressUpdatePayload, isAddressFormDirty,
} from "../../domain/addressForm";
import { CustomerSavedAddress } from "../../domain/customerSavedAddress";
import { CustomerAppStackParamList } from "../../navigation/routeTypes";
import { DomainError } from "../../domain/errors";

const EMPTY_FORM: AddressFormState = {
  label: "Home", fullName: "", addressLine1: "", addressLine2: "", landmark: "",
  city: "", state: "", pinCode: "", isDefault: false,
};

function toFormState(address: CustomerSavedAddress): AddressFormState {
  return {
    label: (address.label === "Home" || address.label === "Work" || address.label === "Other") ? address.label : "Home",
    fullName: address.recipientName ?? "",
    addressLine1: address.line1,
    addressLine2: address.line2 ?? "",
    landmark: address.landmark ?? "",
    city: address.city,
    state: address.state,
    pinCode: address.postalCode,
    isDefault: address.isDefault,
  };
}

type FormRouteProp = RouteProp<CustomerAppStackParamList, "AddAddress" | "EditAddress">;

/**
 * Backs both `AddAddress` and `EditAddress` (spec section 5): edit mode
 * loads the owned address by `addressId` from the canonical API/cache,
 * never trusting a whole address object passed through navigation params.
 */
export function AddressFormScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation();
  const route = useRoute<FormRouteProp>();
  const mode: "add" | "edit" = route.name === "EditAddress" ? "edit" : "add";
  const addressId = mode === "edit" ? (route.params as { addressId: string }).addressId : undefined;

  const addressesQuery = useCustomerAddressesQuery();
  const detailQuery = useCustomerAddressDetailQuery(addressId);
  const createMutation = useCreateAddressMutation();
  const updateMutation = useUpdateAddressMutation(addressId ?? "");

  const [form, setForm] = useState<AddressFormState>(EMPTY_FORM);
  const [original, setOriginal] = useState<AddressFormState>(EMPTY_FORM);
  const [touched, setTouched] = useState<Partial<Record<keyof AddressFormErrors, boolean>>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [loadedOnce, setLoadedOnce] = useState(false);
  const [interacted, setInteracted] = useState(false);

  useEffect(() => {
    if (mode === "edit" && detailQuery.data && !loadedOnce) {
      const next = toFormState(detailQuery.data);
      setForm(next);
      setOriginal(next);
      setLoadedOnce(true);
    }
  }, [mode, detailQuery.data, loadedOnce]);

  if (mode === "edit" && detailQuery.isPending) {
    return (
      <AppScreen>
        <LoadingState label="Loading address" />
      </AppScreen>
    );
  }

  if (mode === "edit" && detailQuery.isError) {
    return (
      <AppScreen>
        <ErrorState
          title="We couldn't load this address"
          actionLabel="Try again"
          onAction={() => detailQuery.refetch()}
        />
      </AppScreen>
    );
  }

  const { errors, valid } = validateAddressForm(form);
  const editDirty = mode === "edit" && isAddressFormDirty(form, original);
  const canSaveDirty = mode === "add" ? true : editDirty;
  const isFirstAddress = mode === "add" && (addressesQuery.data?.length ?? 0) === 0;
  const forcedDefault = mode === "edit" ? original.isDefault : isFirstAddress;
  const forcedReason = mode === "edit" && original.isDefault
    ? "This is your default address. Set another address as default to change it."
    : isFirstAddress
    ? "Your first saved address is automatically your default."
    : undefined;

  const saving = mode === "add" ? createMutation.isPending : updateMutation.isPending;
  const canSave = valid && canSaveDirty && !saving;

  function updateField<K extends keyof AddressFormState>(key: K, value: AddressFormState[K]) {
    setInteracted(true);
    setForm(prev => ({ ...prev, [key]: value }));
  }

  function markTouched(key: keyof AddressFormErrors) {
    setTouched(prev => ({ ...prev, [key]: true }));
  }

  function confirmDiscard(onDiscard: () => void) {
    const shouldConfirm = mode === "edit" ? editDirty : interacted;
    if (!shouldConfirm) {
      onDiscard();
      return;
    }
    Alert.alert("Discard changes?", "Your unsaved address changes will be lost.", [
      { text: "Keep editing", style: "cancel" },
      { text: "Discard", style: "destructive", onPress: onDiscard },
    ]);
  }

  async function handleSave() {
    setServerError(null);
    setTouched({ fullName: true, addressLine1: true, city: true, state: true, pinCode: true });
    if (!valid) return;
    try {
      if (mode === "add") {
        const payload = buildAddressCreatePayload({ ...form, isDefault: forcedDefault || form.isDefault });
        await createMutation.mutateAsync(payload);
      } else {
        const payload = buildAddressUpdatePayload(form, original);
        await updateMutation.mutateAsync(payload);
      }
      navigation.goBack();
    } catch (err) {
      // Preserve entered values on a recoverable failure (spec section 8) --
      // never resets the form here.
      setServerError(err instanceof DomainError ? err.diagnostic : "Couldn't save this address. Please try again.");
    }
  }

  return (
    <AppScreen scroll edges={["top", "bottom"]}>
      <View style={{ gap: theme.spacing.base }}>
        <AddressFormHeader mode={mode} onBack={() => confirmDiscard(() => navigation.goBack())} />
        <AddressAvailabilityInfo />

        <AddressLabelSelector value={form.label} onChange={label => updateField("label", label)} />

        <AddressFormFields
          form={form}
          errors={errors}
          touched={touched}
          onChange={updateField}
          onBlur={markTouched}
        />

        <DefaultAddressToggle
          checked={form.isDefault}
          forced={forcedDefault}
          forcedReason={forcedReason}
          onChange={value => updateField("isDefault", value)}
        />

        <AddressHistoricalNote />

        {serverError ? <AppText variant="bodySmall" color="danger">{serverError}</AppText> : null}

        <AddressFormFooter mode={mode} canSave={canSave} saving={saving} onSave={handleSave} />
      </View>
    </AppScreen>
  );
}
