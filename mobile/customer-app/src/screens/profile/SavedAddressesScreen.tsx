import React, { useState } from "react";
import { View, Alert } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { CustomerAppStackParamList } from "../../navigation/routeTypes";
import { useTheme } from "../../design-system/theme";
import { AppScreen } from "../../components/AppScreen";
import { LoadingState } from "../../components/LoadingState";
import { ErrorState } from "../../components/States";
import { OfflineBanner } from "../../components/OfflineBanner";
import { AppButton } from "../../components/AppButton";
import { AppText } from "../../components/AppText";
import { SavedAddressesHeader } from "../../components/addresses/SavedAddressesHeader";
import { AddressBookingInfo } from "../../components/addresses/AddressBookingInfo";
import { SavedAddressCard } from "../../components/addresses/SavedAddressCard";
import { AddressEmptyState } from "../../components/addresses/AddressEmptyState";
import { BookingSnapshotInfo } from "../../components/addresses/BookingSnapshotInfo";
import { useCustomerAddressesQuery } from "../../api/customerAddresses/useCustomerAddressesQuery";
import { useSetDefaultAddressMutation } from "../../api/customerAddresses/useSetDefaultAddressMutation";
import { useDeleteAddressMutation } from "../../api/customerAddresses/useDeleteAddressMutation";
import { resolveAddressCapabilities } from "../../domain/addressCapabilities";
import { formatSavedAddress } from "../../domain/formatAddress";
import { isOffline } from "../../api/networkState";

/**
 * Opened from Profile -> "Saved addresses". Add/Edit now navigate to the
 * real `AddAddress`/`EditAddress` form (Add/Edit Address phase). Delete
 * and Set-default remain real (confirmed `POST .../set-default`,
 * `DELETE ...` routes, both authorized for the customer role).
 */
type Nav = NativeStackNavigationProp<CustomerAppStackParamList, "SavedAddresses">;

export function SavedAddressesScreen() {
  const { theme } = useTheme();
  const navigation = useNavigation<Nav>();
  const query = useCustomerAddressesQuery();
  const setDefaultMutation = useSetDefaultAddressMutation();
  const deleteMutation = useDeleteAddressMutation();
  const capabilities = resolveAddressCapabilities();
  const [pendingDefaultId, setPendingDefaultId] = useState<string | null>(null);

  if (query.isPending) {
    return (
      <AppScreen>
        <LoadingState label="Loading your addresses" />
      </AppScreen>
    );
  }

  if (query.isError && !query.data) {
    return (
      <AppScreen>
        <ErrorState title="We couldn't load your addresses" actionLabel="Try again" onAction={() => query.refetch()} />
      </AppScreen>
    );
  }

  const addresses = query.data ?? [];
  const defaultAddress = addresses.find(a => a.isDefault) ?? null;
  const otherAddresses = addresses.filter(a => !a.isDefault);

  async function handleSetDefault(addressId: string) {
    if (setDefaultMutation.isPending) return;
    setPendingDefaultId(addressId);
    try {
      await setDefaultMutation.mutateAsync(addressId);
    } finally {
      setPendingDefaultId(null);
    }
  }

  function handleDelete(addressId: string, label: string) {
    Alert.alert(
      "Delete this address?",
      `${label}\n\nConfirmed bookings will keep their stored address.`,
      [
        { text: "Keep address", style: "cancel" },
        {
          text: "Delete", style: "destructive",
          onPress: () => { if (!deleteMutation.isPending) deleteMutation.mutate(addressId); },
        },
      ],
    );
  }

  return (
    <AppScreen scroll edges={["top", "bottom"]}>
      {isOffline() ? <OfflineBanner /> : null}
      <View style={{ gap: theme.spacing.base }}>
        <SavedAddressesHeader
          onBack={() => navigation.goBack()}
          onAddNew={capabilities.canCreate ? () => navigation.navigate("AddAddress") : undefined}
        />
        <AddressBookingInfo />

        {defaultAddress ? (
          <View style={{ gap: theme.spacing.xs }}>
            <AppText variant="labelStrong" color="secondary">Default address</AppText>
            <SavedAddressCard
              address={defaultAddress}
              canEdit={capabilities.canEdit}
              canDelete={capabilities.canDelete}
              onEdit={capabilities.canEdit ? () => navigation.navigate("EditAddress", { addressId: defaultAddress.id }) : undefined}
              onDelete={capabilities.canDelete ? () => handleDelete(defaultAddress.id, defaultAddress.label ?? formatSavedAddress(defaultAddress)) : undefined}
            />
          </View>
        ) : null}

        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">Other addresses</AppText>
          {otherAddresses.length === 0 ? (
            <AddressEmptyState onAddAddress={capabilities.canCreate ? () => navigation.navigate("AddAddress") : undefined} />
          ) : (
            otherAddresses.map(address => (
              <SavedAddressCard
                key={address.id}
                address={address}
                canEdit={capabilities.canEdit}
                canDelete={capabilities.canDelete}
                onEdit={capabilities.canEdit ? () => navigation.navigate("EditAddress", { addressId: address.id }) : undefined}
                onDelete={capabilities.canDelete ? () => handleDelete(address.id, address.label ?? formatSavedAddress(address)) : undefined}
                onSetDefault={capabilities.canSetDefault ? () => handleSetDefault(address.id) : undefined}
                settingDefault={pendingDefaultId === address.id}
              />
            ))
          )}
        </View>

        <BookingSnapshotInfo />

        {capabilities.canCreate ? (
          <AppButton label="Add new address" onPress={() => navigation.navigate("AddAddress")} fullWidth />
        ) : null}
        <AppText variant="caption" color="tertiary" align="center">You can choose a different address during booking.</AppText>
      </View>
    </AppScreen>
  );
}
