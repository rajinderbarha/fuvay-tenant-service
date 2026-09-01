import React from "react";
import { Pressable, ScrollView, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useTheme } from "../../design-system/theme";
import type { BookingReviewSummary } from "../../domain/bookingReview";
import { formatMoney } from "../../domain/money";
import { AppLucideIcon } from "../AppLucideIcon";
import { AppText } from "../AppText";

export interface ReviewSheetProps {
  summary: BookingReviewSummary;
  slotLabel: string | null;
  confirming: boolean;
  confirmDisabledReason: string | null;
  onConfirm: () => void;
  onEditSlot: () => void;
  onEditPhotos: () => void;
  onClose: () => void;
}

function ReviewRow({ label, value }: { label: string; value: string }) {
  const { theme } = useTheme();
  return <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 12 }}><AppText variant="caption" style={{ flex: 1, color: theme.fuvay.surfaces.sub }}>{label}</AppText><AppText variant="labelStrong" align="right" style={{ flex: 1, color: theme.fuvay.surfaces.text }}>{value}</AppText></View>;
}

export function ReviewSheet({ summary, slotLabel, confirming, confirmDisabledReason, onConfirm, onEditSlot, onClose }: ReviewSheetProps) {
  const { theme } = useTheme();
  const insets = useSafeAreaInsets();
  const f = theme.fuvay;
  const payable = summary.inspection ? formatMoney(summary.inspection.visitFee) : null;
  const disabled = confirming || Boolean(confirmDisabledReason);
  const answers = summary.answers.slice(0, 4);
  const addressTitle = summary.address.lines[0] ?? summary.address.city ?? "Service address";
  const addressLine = [...summary.address.lines.slice(1), summary.address.city, summary.address.zipcode].filter(Boolean).join(", ");

  return (
    <View style={{ flex: 1, justifyContent: "flex-end", backgroundColor: theme.colors.mediaScrimStrong }}>
      <View style={{ maxHeight: "92%", borderTopLeftRadius: 30, borderTopRightRadius: 30, overflow: "hidden", backgroundColor: f.surfaces.panel, borderWidth: 1, borderColor: f.surfaces.edge, paddingBottom: Math.max(insets.bottom, 10) }}>
        <View style={{ alignSelf: "center", width: 40, height: 4, borderRadius: 4, marginTop: 13, backgroundColor: f.surfaces.rule }} />
        <View style={{ paddingHorizontal: 20, paddingTop: 13, paddingBottom: 12, flexDirection: "row", alignItems: "flex-start", gap: 12 }}>
          <View style={{ flex: 1 }}><AppText variant="headingSmall" style={{ color: f.surfaces.text, fontSize: 18 }}>Review your booking</AppText><AppText variant="caption" style={{ color: f.surfaces.sub }}>Check the details before you confirm</AppText></View>
          <Pressable accessibilityRole="button" accessibilityLabel="Back to chat" onPress={onClose} style={{ width: 34, height: 34, borderRadius: 17, backgroundColor: f.surfaces.card, borderWidth: 1, borderColor: f.surfaces.edge, alignItems: "center", justifyContent: "center" }}><AppLucideIcon name="close" size={16} color={f.surfaces.sub} /></Pressable>
        </View>

        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 14, gap: 13 }}>
          <View style={{ padding: 15, borderRadius: 18, backgroundColor: f.surfaces.card, borderWidth: 1, borderColor: f.surfaces.edge, gap: 10 }}>
            <AppText variant="metaLabel" style={{ color: f.accents.a2 }}>THE PROBLEM</AppText>
            <ReviewRow label="What needs attention?" value={summary.offeringName} />
            {summary.issueSummary ? <ReviewRow label="What's happening with it?" value={summary.issueSummary} /> : null}
            {answers.map(answer => <ReviewRow key={answer.key} label={answer.label} value={answer.value} />)}
          </View>

          <View style={{ padding: 15, borderRadius: 18, backgroundColor: f.surfaces.card, borderWidth: 1, borderColor: f.surfaces.edge, gap: 13 }}>
            <View style={{ flexDirection: "row", gap: 11, alignItems: "center" }}><View style={{ width: 36, height: 36, borderRadius: 12, backgroundColor: f.soft(f.accents.a2), alignItems: "center", justifyContent: "center" }}><AppLucideIcon name="map-marker-path" size={17} color={f.accents.a2} /></View><View style={{ flex: 1 }}><AppText variant="bodyStrong" style={{ color: f.surfaces.text }}>{addressTitle}</AppText><AppText variant="caption" numberOfLines={1} style={{ color: f.surfaces.sub }}>{addressLine}</AppText></View><Pressable accessibilityRole="button" accessibilityLabel="Change address" onPress={onClose} hitSlop={10}><AppText variant="labelStrong" style={{ color: f.accents.a2 }}>Edit</AppText></Pressable></View>
            <View style={{ height: 1, backgroundColor: f.surfaces.rule }} />
            <View style={{ flexDirection: "row", gap: 11, alignItems: "center" }}><View style={{ width: 36, height: 36, borderRadius: 12, backgroundColor: f.soft(f.accents.a2), alignItems: "center", justifyContent: "center" }}><AppLucideIcon name="calendar-clock" size={17} color={f.accents.a2} /></View><View style={{ flex: 1 }}><AppText variant="bodyStrong" style={{ color: f.surfaces.text }}>{slotLabel ?? "Time to be confirmed"}</AppText><AppText variant="caption" style={{ color: f.surfaces.sub }}>2-hour arrival window</AppText></View><Pressable accessibilityRole="button" accessibilityLabel="Change time" onPress={onEditSlot} hitSlop={10}><AppText variant="labelStrong" style={{ color: f.accents.a2 }}>Edit</AppText></Pressable></View>
          </View>

          <View style={{ padding: 15, borderRadius: 18, backgroundColor: f.surfaces.card, borderWidth: 1, borderColor: f.surfaces.edge, gap: 10 }}>
            <AppText variant="metaLabel" style={{ color: f.surfaces.faint }}>PAYMENT AFTER SERVICE</AppText>
            {payable ? <ReviewRow label="Inspection fee" value={payable} /> : null}
            <ReviewRow label="Parts, if needed" value="Approved by you on site" />
            <View style={{ height: 1, backgroundColor: f.surfaces.rule }} />
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-end", gap: 12 }}><View style={{ flex: 1 }}><AppText variant="bodyStrong" style={{ color: f.surfaces.text }}>Nothing due now</AppText><AppText variant="caption" style={{ color: f.surfaces.sub }}>Pay after inspection or completed work</AppText></View>{payable ? <AppText variant="numericLarge" style={{ color: f.surfaces.text }}>{payable}</AppText> : null}</View>
          </View>

          <View style={{ minHeight: 40, paddingHorizontal: 14, borderRadius: 14, backgroundColor: f.soft(f.accents.a3), flexDirection: "row", alignItems: "center", gap: 9 }}><AppLucideIcon name="shield-check-outline" size={15} color={f.accents.a3} /><AppText variant="caption" style={{ flex: 1, color: f.surfaces.sub }}>Free cancellation up to 2 hours before the visit.</AppText></View>
          {confirmDisabledReason ? <AppText variant="caption" style={{ color: theme.colors.statusDanger }}>{confirmDisabledReason}</AppText> : null}
        </ScrollView>

        <View style={{ paddingHorizontal: 20 }}>
          <Pressable accessibilityRole="button" accessibilityLabel={confirming ? "Confirming" : "Confirm and book"} accessibilityState={{ disabled }} disabled={disabled} onPress={onConfirm} style={{ minHeight: 54, borderRadius: 27, backgroundColor: disabled ? f.surfaces.rule : f.accents.a2, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 9 }}><AppText variant="button" style={{ color: disabled ? f.surfaces.faint : f.ink(f.accents.a2) }}>{confirming ? "Confirming…" : "Confirm booking"}</AppText><AppLucideIcon name="check" size={16} color={disabled ? f.surfaces.faint : f.ink(f.accents.a2)} /></Pressable>
        </View>
      </View>
    </View>
  );
}
