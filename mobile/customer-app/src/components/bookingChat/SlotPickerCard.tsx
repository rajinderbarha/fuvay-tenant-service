import React, { useState } from "react";
import { View, Text, Pressable, ScrollView, ActivityIndicator } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useBotColors } from "./botTheme";
import { BotCard, BotPrimaryButton } from "./BotPrimitives";
import { AvailableSlot, BookingReviewSummary } from "../../domain/bookingReview";

export interface SlotPickerCardProps {
  promisedSlot: BookingReviewSummary["promisedSlot"];
  /** Shown alongside the slot -- there is no per-slot price anywhere in
   * the backend, so every offered time costs the same resolved amount;
   * this is that one real price, not a per-slot fabrication. Null when
   * pricing hasn't resolved to a displayable value (e.g. bargain mode). */
  priceLabel: string | null;
  /** What an emergency visit costs extra with this provider, formatted. Shown
   * ON the emergency option so the extra charge is known before it is tapped,
   * never discovered after a slot is chosen. Null when there is no surcharge. */
  emergencySurchargeLabel: string | null;
  availableSlots: AvailableSlot[] | null;
  slotsLoading: boolean;
  slotSelectionError: string | null;
  onLoadSlots: (emergency: boolean) => void;
  onSelectSlot: (dateIso: string, timeWindow: string, emergency: boolean) => Promise<void>;
  onContinue: () => Promise<void>;
}

function dayLabel(dateIso: string, daysAhead: number): string {
  if (daysAhead === 0) return "Today";
  if (daysAhead === 1) return "Tomorrow";
  const d = new Date(`${dateIso}T00:00:00`);
  if (Number.isNaN(d.getTime())) return dateIso;
  return d.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" });
}

/**
 * Tenant-configured slots, shown to the customer to pick from -- the
 * provider already set up their own business hours and per-slot capacity
 * (`provider_availability_rules`); this just surfaces exactly what that
 * produces via the real, capacity-checked `list_available_slots` walk.
 *
 * Every timing rule lives in the backend, driven by the provider's own
 * booking-window settings -- nothing here is simulated client-side, and no
 * specific number of hours is quoted in this UI because the provider owns
 * that value and can change it:
 *  - a slot must clear the provider's configured notice period
 *    (`minimum_notice_minutes`). "Soonest possible" asks the backend to
 *    waive it, which it does only if that provider enabled
 *    `emergency_booking_allowed` -- it can never conjure a slot outside
 *    their real working hours or capacity.
 *  - once a working day's slots are exhausted, the next options are the
 *    next OPEN day's; there is no invented "after hours" slot.
 *
 * The service price is shown in the SAME card as the slot list (not a
 * separate step) since the customer should see cost and timing together
 * before picking -- there is no per-slot price anywhere in the backend,
 * so every slot costs the same resolved price, never a fabricated
 * time-of-day surcharge.
 */
export function SlotPickerCard({
  promisedSlot, priceLabel, emergencySurchargeLabel, availableSlots,
  slotsLoading, slotSelectionError, onLoadSlots, onSelectSlot, onContinue,
}: SlotPickerCardProps) {
  const BOT = useBotColors();
  const [open, setOpen] = useState(false);
  const [emergency, setEmergency] = useState(false);
  const [pickingKey, setPickingKey] = useState<string | null>(null);
  const [acceptingSuggested, setAcceptingSuggested] = useState(false);

  function openPicker(nextEmergency: boolean) {
    setEmergency(nextEmergency);
    setOpen(true);
    onLoadSlots(nextEmergency);
  }

  async function handlePick(s: AvailableSlot) {
    const key = `${s.date}|${s.timeWindow}`;
    setPickingKey(key);
    try {
      await onSelectSlot(s.date, s.timeWindow, emergency);
      setOpen(false);
    } catch {
      // slotSelectionError below already shows the real reason.
    } finally {
      setPickingKey(null);
    }
  }

  async function handleContinue() {
    if (acceptingSuggested) return;
    setAcceptingSuggested(true);
    try {
      await onContinue();
    } catch {
      // The controller exposes the authoritative slot-selection error in
      // this card. Keep the customer here so they can choose another time.
    } finally {
      setAcceptingSuggested(false);
    }
  }

  return (
    <BotCard>
      <Text style={{ fontSize: 16, fontWeight: "700", color: BOT.textPrimary }}>When should the technician come?</Text>

      {promisedSlot ? (
        <View style={{ marginTop: 10, gap: 6 }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
            <Ionicons name="time-outline" size={15} color={BOT.brand} />
            <Text style={{ fontSize: 15, color: BOT.textSecondary }}>
              {dayLabel(promisedSlot.date, promisedSlot.daysAhead)}, {promisedSlot.timeWindow}
            </Text>
          </View>
          {priceLabel ? (
            <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
              <Ionicons name="pricetag-outline" size={15} color={BOT.brand} />
              <Text style={{ fontSize: 15, color: BOT.textSecondary }}>{priceLabel}</Text>
            </View>
          ) : null}
        </View>
      ) : (
        <Text style={{ fontSize: 15, color: BOT.textMuted, marginTop: 6 }}>
          We can&apos;t promise a time right now -- your provider will contact you to arrange one.
        </Text>
      )}

      <View style={{ flexDirection: "row", gap: 8, marginTop: 12 }}>
        <Pressable
          onPress={() => openPicker(false)}
          accessibilityRole="button"
          accessibilityLabel="Choose a different time"
          style={{ flex: 1, height: 36, borderRadius: 18, alignItems: "center", justifyContent: "center", backgroundColor: BOT.surfaceSunken, borderWidth: 1, borderColor: BOT.border }}
        >
          <Text style={{ fontSize: 13, color: BOT.textSecondary }}>Choose a time</Text>
        </Pressable>
        <Pressable
          onPress={() => openPicker(true)}
          accessibilityRole="button"
          accessibilityLabel="Soonest possible time"
          style={{ flex: 1, height: 36, borderRadius: 18, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, backgroundColor: BOT.brandTint, borderWidth: 1, borderColor: BOT.brand }}
        >
          <Ionicons name="flash" size={13} color={BOT.warning} />
          <Text style={{ fontSize: 13, fontWeight: "600", color: BOT.brandLight }}>
            {emergencySurchargeLabel ? `Soonest (+${emergencySurchargeLabel})` : "Soonest possible"}
          </Text>
        </Pressable>
      </View>

      {promisedSlot ? (
        <View style={{ marginTop: 14 }}>
          <BotPrimaryButton
            label={acceptingSuggested ? "Checking time…" : "Continue"}
            onPress={() => { void handleContinue(); }}
            disabled={acceptingSuggested}
          />
        </View>
      ) : null}

      {open ? (
        <View style={{ marginTop: 14, borderTopWidth: 1, borderTopColor: BOT.borderSubtle, paddingTop: 14 }}>
          <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
            <Text style={{ fontSize: 15, fontWeight: "600", color: BOT.textPrimary }}>
              {emergency ? "Soonest the provider can come" : "Available times"}
            </Text>
            <Pressable onPress={() => setOpen(false)} accessibilityRole="button" accessibilityLabel="Close">
              <Ionicons name="close" size={16} color={BOT.textFaint} />
            </Pressable>
          </View>

          {emergency && emergencySurchargeLabel ? (
            <View
              style={{
                flexDirection: "row", gap: 8, alignItems: "flex-start",
                marginTop: 10, padding: 12, borderRadius: 12, backgroundColor: BOT.brandTint,
              }}
            >
              <Ionicons name="flash" size={14} color={BOT.warning} style={{ marginTop: 2 }} />
              <Text style={{ flex: 1, fontSize: 13, lineHeight: 19, color: BOT.textPrimary }}>
                Coming out at short notice costs{" "}
                <Text style={{ fontWeight: "700" }}>{emergencySurchargeLabel} extra</Text>. It is
                added to the total you approve — never charged later.
              </Text>
            </View>
          ) : null}

          {/* A failed load is recoverable: the customer gets the real reason and
              a way to try again, rather than a dead panel they must close. */}
          {slotSelectionError ? (
            <View style={{ marginTop: 10 }}>
              <Text style={{ fontSize: 13, color: BOT.danger }}>{slotSelectionError}</Text>
              <Pressable
                onPress={() => onLoadSlots(emergency)}
                accessibilityRole="button"
                accessibilityLabel="Try loading times again"
                style={{
                  alignSelf: "flex-start", flexDirection: "row", alignItems: "center", gap: 6,
                  marginTop: 8, paddingHorizontal: 12, height: 34, borderRadius: 17,
                  backgroundColor: BOT.surfaceSunken, borderWidth: 1, borderColor: BOT.border,
                }}
              >
                <Ionicons name="refresh" size={13} color={BOT.textSecondary} />
                <Text style={{ fontSize: 13, fontWeight: "600", color: BOT.textSecondary }}>
                  Try again
                </Text>
              </Pressable>
            </View>
          ) : null}

          {slotsLoading && !availableSlots ? (
            <ActivityIndicator color={BOT.brand} style={{ marginTop: 12 }} />
          ) : availableSlots && availableSlots.length === 0 ? (
            <Text style={{ fontSize: 15, color: BOT.textMuted, marginTop: 10 }}>
              No times available{emergency ? " even at the earliest" : ""}. Your provider will contact you to arrange one.
            </Text>
          ) : (
            <ScrollView style={{ maxHeight: 220, marginTop: 10 }}>
              <View style={{ gap: 8 }}>
                {(availableSlots ?? []).map(s => {
                  const key = `${s.date}|${s.timeWindow}`;
                  const isCurrent = promisedSlot?.date === s.date && promisedSlot?.timeWindow === s.timeWindow;
                  const isBusy = pickingKey === key;
                  return (
                    <Pressable
                      key={key}
                      onPress={() => handlePick(s)}
                      disabled={isCurrent || pickingKey !== null}
                      accessibilityRole="button"
                      accessibilityLabel={`${dayLabel(s.date, s.daysAhead)}, ${s.timeWindow}${isCurrent ? ", currently selected" : ""}`}
                      style={{
                        flexDirection: "row", alignItems: "center", justifyContent: "space-between",
                        height: 44, paddingHorizontal: 14, borderRadius: 12,
                        backgroundColor: isCurrent ? BOT.brandTint : BOT.surfaceSunken,
                        borderWidth: 1, borderColor: isCurrent ? BOT.brand : BOT.borderSubtle,
                        opacity: pickingKey !== null && !isBusy ? 0.5 : 1,
                      }}
                    >
                      <Text style={{ fontSize: 15, color: BOT.textSecondary }}>{dayLabel(s.date, s.daysAhead)}, {s.timeWindow}</Text>
                      {isBusy ? (
                        <ActivityIndicator size="small" color={BOT.brand} />
                      ) : isCurrent ? (
                        <Ionicons name="checkmark-circle" size={16} color={BOT.brand} />
                      ) : null}
                    </Pressable>
                  );
                })}
              </View>
            </ScrollView>
          )}
        </View>
      ) : null}
    </BotCard>
  );
}
