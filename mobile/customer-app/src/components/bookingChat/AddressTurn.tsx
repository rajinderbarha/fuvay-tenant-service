import React, { useState } from "react";
import { View, Text, Pressable, TextInput, ActivityIndicator } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { BOT } from "./botTheme";
import { BotCard, BotPrimaryButton } from "./BotPrimitives";
import { CustomerSavedAddress } from "../../domain/customerSavedAddress";
import { AddressCreatePayload } from "../../domain/addressForm";

export interface AddressTurnProps {
  zipcode: string;
  addresses: CustomerSavedAddress[] | null;
  loading: boolean;
  submitting: boolean;
  error: string | null;
  onPickExisting: (addressId: string) => void;
  onCreateNew: (payload: AddressCreatePayload) => void;
}

/**
 * Address step inside the merged chat.
 *
 * Zipcode is NEVER editable here, by explicit product rule: the assigned
 * provider was matched against the entry zipcode, and the backend's own
 * `update_draft_fields` overwrites `draft.zipcode` from whatever address
 * is attached -- so only an address whose OWN zipcode already equals this
 * one may ever be offered or created. Saved addresses with a different
 * zip are filtered out entirely (shown as a plain count, never picked);
 * the "add new" form's zip field is pre-filled and disabled.
 */
export function AddressTurn({ zipcode, addresses, loading, submitting, error, onPickExisting, onCreateNew }: AddressTurnProps) {
  const [showForm, setShowForm] = useState(false);
  const [line1, setLine1] = useState("");
  const [line2, setLine2] = useState("");
  const [landmark, setLandmark] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [label, setLabel] = useState("Home");

  const matching = (addresses ?? []).filter(a => a.postalCode === zipcode);
  const excludedCount = (addresses ?? []).length - matching.length;
  const canSubmit = line1.trim().length > 0 && city.trim().length > 0 && state.trim().length > 0;

  function submitNew() {
    if (!canSubmit) return;
    onCreateNew({
      label, name: null,
      address_line_1: line1.trim(), address_line_2: line2.trim() || null, landmark: landmark.trim() || null,
      city: city.trim(), state: state.trim(), zipcode, is_default: matching.length === 0,
    });
  }

  if (loading) {
    return (
      <BotCard>
        <ActivityIndicator color={BOT.brand} />
      </BotCard>
    );
  }

  return (
    <BotCard>
      <Text style={{ fontSize: 14, fontWeight: "700", color: BOT.textPrimary }}>Where should the technician come?</Text>
      <Text style={{ fontSize: 11.5, color: BOT.textMuted, marginTop: 2 }}>
        Only addresses in {zipcode} -- the professional matched is local to this zip.
      </Text>

      {matching.length > 0 ? (
        <View style={{ marginTop: 12, gap: 8 }}>
          {matching.map(a => (
            <Pressable
              key={a.id}
              onPress={() => onPickExisting(a.id)}
              disabled={submitting}
              accessibilityRole="button"
              accessibilityLabel={`${a.label ?? "Address"}, ${a.line1}`}
              style={{
                flexDirection: "row", alignItems: "flex-start", gap: 10,
                padding: 12, borderRadius: 14, backgroundColor: BOT.surfaceSunken, borderWidth: 1, borderColor: BOT.borderSubtle,
              }}
            >
              <Ionicons name="home" size={16} color={BOT.brand} style={{ marginTop: 1 }} />
              <View style={{ flex: 1, minWidth: 0 }}>
                <Text style={{ fontSize: 12.5, fontWeight: "600", color: BOT.textPrimary }}>{a.label ?? "Address"}</Text>
                <Text style={{ fontSize: 11.5, color: BOT.textMuted, marginTop: 1 }} numberOfLines={2}>
                  {[a.line1, a.line2, a.city, a.postalCode].filter(Boolean).join(", ")}
                </Text>
              </View>
              <Ionicons name="chevron-forward" size={16} color={BOT.textFaint} />
            </Pressable>
          ))}
        </View>
      ) : null}

      {excludedCount > 0 && matching.length === 0 ? (
        <Text style={{ fontSize: 11, color: BOT.textDim, marginTop: 10 }}>
          {excludedCount} saved address{excludedCount === 1 ? "" : "es"} outside {zipcode} — not shown here.
        </Text>
      ) : null}

      {error ? <Text style={{ fontSize: 12, color: BOT.danger, marginTop: 10 }}>{error}</Text> : null}

      {!showForm ? (
        <Pressable onPress={() => setShowForm(true)} style={{ marginTop: 12, flexDirection: "row", alignItems: "center", gap: 6 }}>
          <Ionicons name="add-circle-outline" size={16} color={BOT.brandLight} />
          <Text style={{ fontSize: 12.5, fontWeight: "600", color: BOT.brandLight }}>Add a new address in {zipcode}</Text>
        </Pressable>
      ) : (
        <View style={{ marginTop: 14, gap: 8 }}>
          {([
            ["Label (Home/Work/Other)", label, setLabel],
            ["Address line 1", line1, setLine1],
            ["Address line 2 (optional)", line2, setLine2],
            ["Landmark (optional)", landmark, setLandmark],
            ["City", city, setCity],
            ["State", state, setState],
          ] as const).map(([placeholder, value, setter]) => (
            <TextInput
              key={placeholder}
              value={value}
              onChangeText={setter}
              placeholder={placeholder}
              placeholderTextColor={BOT.textFaint}
              style={{
                height: 40, borderRadius: 10, paddingHorizontal: 12,
                backgroundColor: BOT.surfaceSunken, borderWidth: 1, borderColor: BOT.borderSubtle,
                color: BOT.textPrimary, fontSize: 12.5,
              }}
            />
          ))}
          {/* Zipcode is shown, never editable -- see component doc. */}
          <View style={{ height: 40, borderRadius: 10, paddingHorizontal: 12, justifyContent: "center", backgroundColor: BOT.surfaceRaised, borderWidth: 1, borderColor: BOT.border }}>
            <Text style={{ fontSize: 12.5, color: BOT.textMuted }}>ZIP {zipcode} (fixed to this request)</Text>
          </View>
          <View style={{ marginTop: 4 }}>
            <BotPrimaryButton label="Save & use this address" onPress={submitNew} disabled={!canSubmit || submitting} loading={submitting} />
          </View>
        </View>
      )}
    </BotCard>
  );
}
