import React, { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Pressable, TextInput, View } from "react-native";

import { useTheme } from "../../design-system/theme";
import type { AddressCreatePayload, AddressLabel } from "../../domain/addressForm";
import type { CustomerSavedAddress } from "../../domain/customerSavedAddress";
import { AppLucideIcon, type AppLucideName } from "../AppLucideIcon";
import { AppText } from "../AppText";
import { FuvayIcon } from "../FuvayIcon";
import { BotPrimaryButton } from "./BotPrimitives";
import { FuvayAssistantSheet } from "./FuvayAssistantSheet";

export interface AddressTurnProps {
  zipcode: string;
  addresses: CustomerSavedAddress[] | null;
  loading: boolean;
  submitting: boolean;
  error: string | null;
  onPickExisting: (addressId: string) => void;
  onCreateNew: (payload: AddressCreatePayload) => void;
}

type Sheet = "addresses" | "new" | null;

const ADDRESS_OPTIONS: ReadonlyArray<{ value: AddressLabel; display: string }> = [
  { value: "Home", display: "Home" },
  { value: "Work", display: "Office" },
  { value: "Other", display: "Other" },
];

function displayAddressLabel(label: string | null): string {
  return /work|office/i.test(label ?? "") ? "Office" : label ?? "Home";
}

function addressIcon(label: string | null): AppLucideName {
  if (/office|work/i.test(label ?? "")) return "cube";
  if (/parent|family/i.test(label ?? "")) return "account-outline";
  return "home-outline";
}

export function AddressTurn({ zipcode, addresses, loading, submitting, error, onPickExisting, onCreateNew }: AddressTurnProps) {
  const { theme } = useTheme();
  const f = theme.fuvay;
  const [sheet, setSheet] = useState<Sheet>(null);
  const didAutoOpen = useRef(false);
  const [label, setLabel] = useState<AddressLabel>("Home");
  const [fullName, setFullName] = useState("");
  const [line1, setLine1] = useState("");
  const [line2, setLine2] = useState("");
  const [landmark, setLandmark] = useState("");
  const [city, setCity] = useState("");
  const [region, setRegion] = useState("");
  const matching = (addresses ?? []).filter(address => address.postalCode === zipcode);
  const chosen = matching.find(address => address.isDefault) ?? matching[0] ?? null;
  const usedLabels = new Set((addresses ?? []).map(address => /work|office/i.test(address.label ?? "") ? "Work" : address.label));
  const availableOptions = ADDRESS_OPTIONS.filter(option => !usedLabels.has(option.value));
  const canAddAddress = availableOptions.length > 0;
  const canSave = !usedLabels.has(label) && line1.trim().length >= 2 && city.trim().length > 0 && region.trim().length > 0;

  useEffect(() => {
    if (!loading && addresses !== null && !didAutoOpen.current) {
      didAutoOpen.current = true;
      setSheet("addresses");
    }
  }, [addresses, loading]);

  function selectAddress(address: CustomerSavedAddress) {
    setSheet(null);
    onPickExisting(address.id);
  }

  function openNewAddress() {
    const firstAvailable = availableOptions[0];
    if (!firstAvailable) return;
    setLabel(firstAvailable.value);
    setSheet("new");
  }

  function saveAddress() {
    if (!canSave) return;
    onCreateNew({
      label,
      name: fullName.trim() || null,
      address_line_1: line1.trim(),
      address_line_2: line2.trim() || null,
      landmark: landmark.trim() || null,
      city: city.trim(),
      state: region.trim(),
      zipcode,
      is_default: (addresses ?? []).length === 0,
      latitude: null,
      longitude: null,
    });
  }

  return (
    <View style={{ gap: 14 }}>
      <View style={{ flexDirection: "row", alignItems: "flex-start", gap: 10 }}>
        <View style={{ width: 32, height: 32, borderRadius: 16, alignItems: "center", justifyContent: "center", backgroundColor: f.surfaces.card, borderWidth: 1, borderColor: f.surfaces.edge }}>
          <FuvayIcon size={17} accessibilityLabel="Fuvay booking assistant" />
        </View>
        <View style={{ flex: 1, paddingHorizontal: 15, paddingVertical: 13, borderRadius: 18, borderTopLeftRadius: 4, backgroundColor: f.surfaces.card, borderWidth: 1, borderColor: f.surfaces.edge }}>
          <AppText variant="bodyStrong" style={{ color: f.surfaces.text }}>Where should the technician come?</AppText>
        </View>
      </View>

      {chosen ? (
        <Pressable accessibilityRole="button" accessibilityLabel="Change service address" onPress={() => setSheet("addresses")} style={({ pressed }) => ({ marginLeft: 42, alignSelf: "flex-end", maxWidth: "78%", paddingHorizontal: 14, paddingVertical: 11, borderRadius: 16, backgroundColor: f.soft(f.accents.a2), borderWidth: 1, borderColor: f.surfaces.edge, flexDirection: "row", alignItems: "center", gap: 10, opacity: pressed ? theme.opacity.pressed : 1 })}>
          <AppLucideIcon name="map-marker-path" size={16} color={f.accents.a2} />
          <View style={{ flex: 1 }}>
            <AppText variant="bodyStrong" style={{ color: f.surfaces.text }}>{displayAddressLabel(chosen.label)}</AppText>
            <AppText numberOfLines={1} variant="caption" style={{ color: f.surfaces.sub }}>{[chosen.line1, chosen.city, chosen.postalCode].filter(Boolean).join(", ")}</AppText>
          </View>
          <AppLucideIcon name="pencil" size={13} color={f.accents.a2} />
        </Pressable>
      ) : loading ? <ActivityIndicator color={f.accents.a2} /> : (
        <Pressable accessibilityRole="button" accessibilityLabel="Choose service address" onPress={() => setSheet("addresses")} style={{ marginLeft: 42, minHeight: 44, borderRadius: 22, borderWidth: 1, borderColor: f.accents.a2, alignItems: "center", justifyContent: "center" }}>
          <AppText variant="button" style={{ color: f.accents.a2 }}>Choose service address</AppText>
        </Pressable>
      )}

      {error ? <AppText variant="caption" style={{ marginLeft: 42, color: theme.colors.statusDanger }}>{error}</AppText> : null}

      <FuvayAssistantSheet
        visible={sheet === "addresses"}
        title="Service address"
        onClose={() => setSheet(null)}
      >
        <AppText variant="metaLabel" style={{ color: f.surfaces.faint }}>SAVED ADDRESSES</AppText>
        <View style={{ gap: 10 }}>
          {matching.map((address, index) => {
            const selected = address.id === chosen?.id;
            return (
              <Pressable key={address.id} accessibilityRole="button" accessibilityLabel={`${address.label ?? "Address"}, ${address.line1}`} disabled={submitting} onPress={() => selectAddress(address)} style={({ pressed }) => ({ minHeight: 60, paddingHorizontal: 13, paddingVertical: 10, borderRadius: 14, backgroundColor: selected ? f.soft(f.accents.a2) : f.surfaces.card, borderWidth: selected ? 1.5 : 1, borderColor: selected ? f.accents.a2 : f.surfaces.edge, flexDirection: "row", alignItems: "center", gap: 11, opacity: pressed ? theme.opacity.pressed : 1 })}>
                <View style={{ width: 36, height: 36, borderRadius: 12, alignItems: "center", justifyContent: "center", backgroundColor: f.soft(selected ? f.accents.a2 : f.tile.icon) }}>
                  <AppLucideIcon name={addressIcon(address.label)} size={17} color={selected ? f.accents.a2 : f.surfaces.sub} />
                </View>
                <View style={{ flex: 1 }}>
                  <AppText variant="bodyStrong" style={{ color: f.surfaces.text }}>{address.label ? displayAddressLabel(address.label) : `Address ${index + 1}`}</AppText>
                  <AppText variant="caption" numberOfLines={1} style={{ color: f.surfaces.sub }}>{[address.line1, address.city, address.postalCode].filter(Boolean).join(", ")}</AppText>
                </View>
                {selected ? <View style={{ width: 20, height: 20, borderRadius: 10, backgroundColor: f.accents.a2, alignItems: "center", justifyContent: "center" }}><AppLucideIcon name="check" size={12} color={f.ink(f.accents.a2)} /></View> : null}
              </Pressable>
            );
          })}
        </View>
        <Pressable accessibilityRole="button" accessibilityLabel="Add a new address" accessibilityState={{ disabled: !canAddAddress }} disabled={!canAddAddress} onPress={openNewAddress} style={{ minHeight: 52, borderRadius: 14, borderWidth: 1.5, borderColor: canAddAddress ? f.accents.a2 : f.surfaces.rule, paddingHorizontal: 14, flexDirection: "row", alignItems: "center", gap: 11, opacity: canAddAddress ? 1 : 0.62 }}>
          <AppLucideIcon name={canAddAddress ? "plus" : "check"} size={16} color={canAddAddress ? f.accents.a2 : f.surfaces.faint} />
          <AppText variant="labelStrong" style={{ color: canAddAddress ? f.accents.a2 : f.surfaces.faint }}>{canAddAddress ? "Add a new address" : "Home, Office and Other already saved"}</AppText>
        </Pressable>
      </FuvayAssistantSheet>

      <FuvayAssistantSheet visible={sheet === "new"} title="New address" onClose={() => setSheet("addresses")} scroll>
        <AppText variant="metaLabel" style={{ color: f.surfaces.faint }}>SAVE AS</AppText>
        <View style={{ flexDirection: "row", gap: 8 }}>
          {ADDRESS_OPTIONS.map(option => {
            const selected = option.value === label;
            const unavailable = usedLabels.has(option.value);
            return <Pressable key={option.value} accessibilityRole="button" accessibilityState={{ selected, disabled: unavailable }} disabled={unavailable} onPress={() => setLabel(option.value)} style={{ minHeight: 40, paddingHorizontal: 16, borderRadius: 20, alignItems: "center", justifyContent: "center", backgroundColor: selected ? f.accents.a2 : f.surfaces.card, borderWidth: 1, borderColor: selected ? f.accents.a2 : f.surfaces.edge, opacity: unavailable ? 0.42 : 1 }}><AppText variant="labelStrong" style={{ color: selected ? f.ink(f.accents.a2) : f.surfaces.sub }}>{option.display}</AppText></Pressable>;
          })}
        </View>
        <AppText variant="metaLabel" style={{ color: f.surfaces.faint }}>RECIPIENT NAME (OPTIONAL)</AppText>
        <TextInput accessibilityLabel="Recipient name" value={fullName} onChangeText={setFullName} placeholder="Full name" placeholderTextColor={f.surfaces.faint} style={[theme.typography.body, { minHeight: 52, borderRadius: 14, paddingHorizontal: 14, color: f.surfaces.text, backgroundColor: f.surfaces.card, borderWidth: 1, borderColor: f.surfaces.edge }]} />
        <AppText variant="metaLabel" style={{ color: f.surfaces.faint }}>FLAT, BUILDING &amp; STREET</AppText>
        <TextInput accessibilityLabel="Flat, building and street" value={line1} onChangeText={setLine1} placeholder="e.g. 14 Model Town, Block B" placeholderTextColor={f.surfaces.faint} style={[theme.typography.body, { minHeight: 52, borderRadius: 14, paddingHorizontal: 14, color: f.surfaces.text, backgroundColor: f.surfaces.card, borderWidth: 1, borderColor: f.surfaces.edge }]} />
        <AppText variant="metaLabel" style={{ color: f.surfaces.faint }}>APARTMENT, FLOOR OR AREA (OPTIONAL)</AppText>
        <TextInput accessibilityLabel="Apartment floor or area" value={line2} onChangeText={setLine2} placeholder="Apartment, floor, area or locality" placeholderTextColor={f.surfaces.faint} style={[theme.typography.body, { minHeight: 52, borderRadius: 14, paddingHorizontal: 14, color: f.surfaces.text, backgroundColor: f.surfaces.card, borderWidth: 1, borderColor: f.surfaces.edge }]} />
        <AppText variant="metaLabel" style={{ color: f.surfaces.faint }}>LANDMARK (OPTIONAL)</AppText>
        <TextInput accessibilityLabel="Landmark" value={landmark} onChangeText={setLandmark} placeholder="Nearby landmark" placeholderTextColor={f.surfaces.faint} style={[theme.typography.body, { minHeight: 52, borderRadius: 14, paddingHorizontal: 14, color: f.surfaces.text, backgroundColor: f.surfaces.card, borderWidth: 1, borderColor: f.surfaces.edge }]} />
        <AppText variant="metaLabel" style={{ color: f.surfaces.faint }}>CITY</AppText>
        <TextInput accessibilityLabel="City" value={city} onChangeText={setCity} placeholder="City" placeholderTextColor={f.surfaces.faint} style={[theme.typography.body, { minHeight: 52, borderRadius: 14, paddingHorizontal: 14, color: f.surfaces.text, backgroundColor: f.surfaces.card, borderWidth: 1, borderColor: f.surfaces.edge }]} />
        <AppText variant="metaLabel" style={{ color: f.surfaces.faint }}>STATE</AppText>
        <TextInput accessibilityLabel="State" value={region} onChangeText={setRegion} placeholder="State" placeholderTextColor={f.surfaces.faint} style={[theme.typography.body, { minHeight: 52, borderRadius: 14, paddingHorizontal: 14, color: f.surfaces.text, backgroundColor: f.surfaces.card, borderWidth: 1, borderColor: f.surfaces.edge }]} />
        <AppText variant="metaLabel" style={{ color: f.surfaces.faint }}>PINCODE</AppText>
        <View style={{ minHeight: 52, borderRadius: 14, paddingHorizontal: 14, backgroundColor: f.surfaces.card, borderWidth: 1, borderColor: f.surfaces.edge, flexDirection: "row", alignItems: "center", gap: 10 }}>
          <TextInput accessibilityLabel="Pincode, automatically filled" value={zipcode} editable={false} selectTextOnFocus={false} style={[theme.typography.body, { flex: 1, color: f.surfaces.sub }]} />
          <AppLucideIcon name="shield-check-outline" size={15} color={f.surfaces.faint} />
        </View>
        <View style={{ minHeight: 40, paddingHorizontal: 13, borderRadius: 13, backgroundColor: f.soft(f.accents.a2), flexDirection: "row", alignItems: "center", gap: 9 }}><AppLucideIcon name="map-marker-path" size={14} color={f.accents.a2} /><AppText variant="caption" style={{ flex: 1, color: f.surfaces.sub }}>We only share the address with the assigned technician.</AppText></View>
        <BotPrimaryButton label="Save address  ✓" onPress={saveAddress} disabled={!canSave || submitting} loading={submitting} />
      </FuvayAssistantSheet>
    </View>
  );
}
