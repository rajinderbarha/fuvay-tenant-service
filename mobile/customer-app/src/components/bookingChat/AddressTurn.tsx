import React, { useState } from "react";
import { View, Pressable, TextInput, ActivityIndicator } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useBotColors } from "./botTheme";
import { BotCard, BotPrimaryButton } from "./BotPrimitives";
import { CustomerSavedAddress } from "../../domain/customerSavedAddress";
import { AddressCreatePayload } from "../../domain/addressForm";
import { AddressSearchField } from "../AddressSearchField";
import { useAddressAutocomplete } from "../../hooks/useAddressAutocomplete";
import { BotText } from "./BotText";

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
  const BOT = useBotColors();
  const [showForm, setShowForm] = useState(false);
  const [line1, setLine1] = useState("");
  const [line2, setLine2] = useState("");
  const [landmark, setLandmark] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [label, setLabel] = useState("Home");
  // Coordinates only ever come from a resolved lookup -- never typed, never guessed.
  const [latitude, setLatitude] = useState<number | null>(null);
  const [longitude, setLongitude] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const autocomplete = useAddressAutocomplete();
  /** Same rule as the saved-address form: search first, type only what the lookup
   * cannot know. With every field on screen people typed all of it and the lookup went
   * unused, so no address carried a real point. Never a wall -- "type it instead" is
   * always offered, and it is the only path when no lookup is configured. */
  const [manualEntry, setManualEntry] = useState(false);
  const [placeChosen, setPlaceChosen] = useState(false);
  const detailsRevealed = manualEntry || placeChosen || !autocomplete.available;

  const matching = (addresses ?? []).filter(a => a.postalCode === zipcode);
  const excludedCount = (addresses ?? []).length - matching.length;
  const canSubmit = line1.trim().length > 0 && city.trim().length > 0 && state.trim().length > 0;

  function onSearchChange(value: string) {
    setSearch(value);
    autocomplete.setQuery(value);
  }

  async function pickSuggestion(placeId: string) {
    const resolved = await autocomplete.select(placeId);
    if (!resolved) return;
    setSearch(resolved.formattedAddress ?? "");
    setPlaceChosen(true);
    // Each field is filled only if Google actually returned it, so a partial
    // result never blanks out something the customer already typed.
    if (resolved.line1) setLine1(resolved.line1);
    if (resolved.city) setCity(resolved.city);
    if (resolved.state) setState(resolved.state);
    // The resolved PIN is deliberately DISCARDED here. This request's zipcode is
    // fixed to the one the provider was matched against (see component doc); a
    // Google PIN that disagrees would either be silently ignored or break the
    // match, so the search is used for street/city/state and coordinates only.
    setLatitude(resolved.latitude);
    setLongitude(resolved.longitude);
  }

  function submitNew() {
    if (!canSubmit) return;
    onCreateNew({
      label, name: null,
      address_line_1: line1.trim(), address_line_2: line2.trim() || null, landmark: landmark.trim() || null,
      city: city.trim(), state: state.trim(), zipcode, is_default: matching.length === 0,
      latitude, longitude,
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
      <BotText style={{ fontSize: 16, fontWeight: "700", color: BOT.textPrimary }}>Where should the technician come?</BotText>
      <BotText style={{ fontSize: 13, color: BOT.textMuted, marginTop: 2 }}>
        Only addresses in {zipcode} -- the professional matched is local to this zip.
      </BotText>

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
                <BotText style={{ fontSize: 15, fontWeight: "600", color: BOT.textPrimary }}>{a.label ?? "Address"}</BotText>
                <BotText style={{ fontSize: 13, color: BOT.textMuted, marginTop: 1 }} numberOfLines={2}>
                  {[a.line1, a.line2, a.city, a.postalCode].filter(Boolean).join(", ")}
                </BotText>
              </View>
              <Ionicons name="chevron-forward" size={16} color={BOT.textFaint} />
            </Pressable>
          ))}
        </View>
      ) : null}

      {excludedCount > 0 && matching.length === 0 ? (
        <BotText style={{ fontSize: 12, color: BOT.textDim, marginTop: 10 }}>
          {excludedCount} saved address{excludedCount === 1 ? "" : "es"} outside {zipcode} — not shown here.
        </BotText>
      ) : null}

      {error ? <BotText style={{ fontSize: 13, color: BOT.danger, marginTop: 10 }}>{error}</BotText> : null}

      {!showForm ? (
        <Pressable onPress={() => setShowForm(true)} style={{ marginTop: 12, flexDirection: "row", alignItems: "center", gap: 6 }}>
          <Ionicons name="add-circle-outline" size={16} color={BOT.brandLight} />
          <BotText style={{ fontSize: 15, fontWeight: "600", color: BOT.brandLight }}>Add a new address in {zipcode}</BotText>
        </Pressable>
      ) : (
        <View style={{ marginTop: 14, gap: 8 }}>
          <AddressSearchField
            value={search}
            onChangeText={onSearchChange}
            suggestions={autocomplete.suggestions}
            available={autocomplete.available}
            searching={autocomplete.searching}
            resolving={autocomplete.resolving}
            onSelect={pickSuggestion}
            palette={{
              surface: BOT.surfaceSunken, border: BOT.borderSubtle,
              text: BOT.textPrimary, placeholder: BOT.textFaint, muted: BOT.textMuted,
            }}
          />
          {!detailsRevealed ? (
            <Pressable
              onPress={() => setManualEntry(true)}
              accessibilityRole="button"
              accessibilityLabel="Type the address instead"
              style={{ paddingVertical: 8 }}
            >
              <BotText style={{ fontSize: 13, fontWeight: "600", color: BOT.brandLight }}>
                Type the address instead
              </BotText>
            </Pressable>
          ) : null}

          {(detailsRevealed ? [
            ["Label (Home/Work/Other)", label, setLabel],
            ["Address line 1", line1, setLine1],
            ["Address line 2 (optional)", line2, setLine2],
            ["Landmark (optional)", landmark, setLandmark],
            ["City", city, setCity],
            ["State", state, setState],
          ] as const : []).map(([placeholder, value, setter]) => (
            <TextInput
              key={placeholder}
              value={value}
              onChangeText={setter}
              placeholder={placeholder}
              placeholderTextColor={BOT.textFaint}
              style={{
                height: 40, borderRadius: 10, paddingHorizontal: 12,
                backgroundColor: BOT.surfaceSunken, borderWidth: 1, borderColor: BOT.borderSubtle,
                color: BOT.textPrimary, fontSize: 15,
              }}
            />
          ))}
          {detailsRevealed ? (
            <>
              {/* Zipcode is shown, never editable -- see component doc. */}
              <View style={{ height: 40, borderRadius: 10, paddingHorizontal: 12, justifyContent: "center", backgroundColor: BOT.surfaceRaised, borderWidth: 1, borderColor: BOT.border }}>
                <BotText style={{ fontSize: 15, color: BOT.textMuted }}>ZIP {zipcode} (fixed to this request)</BotText>
              </View>
              <View style={{ marginTop: 4 }}>
                <BotPrimaryButton label="Save & use this address" onPress={submitNew} disabled={!canSubmit || submitting} loading={submitting} />
              </View>
            </>
          ) : null}
        </View>
      )}
    </BotCard>
  );
}
