import React from "react";
import { View } from "react-native";

import { useTheme } from "../../design-system/theme";
import type { BookingReviewSummary } from "../../domain/bookingReview";
import { formatMoney } from "../../domain/money";
import { resolveServicePriceDisplay } from "../../domain/servicePricing";
import type { ServiceChecklist } from "../../domain/serviceChecklist";
import { AppLucideIcon } from "../AppLucideIcon";
import { AppText } from "../AppText";
import { BotPrimaryButton } from "./BotPrimitives";

export interface TechnicianQuoteCardProps {
  summary: BookingReviewSummary;
  checklist: ServiceChecklist | null;
  onContinue: () => void;
}

function visitPrice(summary: BookingReviewSummary): string {
  if (summary.inspection) return formatMoney(summary.inspection.visitFee);
  if (summary.priceState.kind === "valid") return formatMoney(summary.priceState.amount);
  return resolveServicePriceDisplay(summary.priceState).label;
}

/** The price/coverage panel from the supplied assistant reference, backed only
 * by the actual review summary and provider-authored checklist. */
export function TechnicianQuoteCard({ summary, checklist, onContinue }: TechnicianQuoteCardProps) {
  const { theme } = useTheme();
  const f = theme.fuvay;
  const points = (checklist?.sections ?? []).flatMap(section => section.points);
  const shown = points.slice(0, 6);

  return (
    <View style={{ gap: 14 }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
        <AppLucideIcon name="sparkles" size={15} color={f.accents.a3} />
        <AppText variant="metaLabel" style={{ color: f.accents.a3 }}>TECHNICIAN AVAILABLE</AppText>
      </View>

      <View style={{ padding: 18, borderRadius: 22, borderWidth: 1, borderColor: f.surfaces.edge, backgroundColor: f.surfaces.card, alignItems: "center" }}>
        <AppText variant="metaLabel" style={{ color: f.surfaces.sub }}>FIXED VISIT PRICE</AppText>
        <AppText variant="display" style={{ marginTop: 8, color: f.surfaces.text, fontSize: 42, lineHeight: 46 }}>{visitPrice(summary)}</AppText>
        <AppText variant="caption" align="center" style={{ maxWidth: 245, marginTop: 6, color: f.surfaces.sub }}>
          Diagnosis included and adjusted against the repair. Parts quoted on site before any work.
        </AppText>
        <View style={{ width: "100%", height: 1, marginVertical: 17, backgroundColor: f.surfaces.rule }} />
        <View style={{ width: "100%", flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
          {summary.provider?.facts?.verified ? (
            <View style={{ minHeight: 30, paddingHorizontal: 11, borderRadius: 15, borderWidth: 1, borderColor: f.surfaces.edge, flexDirection: "row", alignItems: "center", gap: 6 }}>
              <AppLucideIcon name="shield-check-outline" size={13} color={f.accents.a2} />
              <AppText variant="caption" style={{ color: f.surfaces.sub }}>Verified pro</AppText>
            </View>
          ) : null}
          <View style={{ minHeight: 30, paddingHorizontal: 11, borderRadius: 15, borderWidth: 1, borderColor: f.surfaces.edge, flexDirection: "row", alignItems: "center", gap: 6 }}>
            <AppLucideIcon name="check" size={13} color={f.accents.a3} />
            <AppText variant="caption" style={{ color: f.surfaces.sub }}>Price confirmed</AppText>
          </View>
        </View>
      </View>

      {shown.length ? (
        <View style={{ padding: 17, borderRadius: 22, borderWidth: 1, borderColor: f.surfaces.edge, backgroundColor: f.surfaces.card, gap: 12 }}>
          <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
            <AppText variant="bodyStrong" style={{ color: f.surfaces.text }}>What's covered</AppText>
            <View style={{ paddingHorizontal: 10, paddingVertical: 4, borderRadius: 99, backgroundColor: f.soft(f.accents.a3) }}>
              <AppText variant="metaLabel" style={{ color: f.accents.a3 }}>{shown.length} OF {points.length}</AppText>
            </View>
          </View>
          {shown.map(point => (
            <View key={point.id} style={{ flexDirection: "row", alignItems: "flex-start", gap: 10 }}>
              <View style={{ width: 22, height: 22, borderRadius: 7, alignItems: "center", justifyContent: "center", backgroundColor: f.soft(f.accents.a3) }}>
                <AppLucideIcon name="check" size={13} color={f.accents.a3} />
              </View>
              <AppText variant="bodySmall" style={{ flex: 1, color: f.surfaces.text }}>{point.label}</AppText>
            </View>
          ))}
          <View style={{ marginTop: 3, paddingTop: 12, borderTopWidth: 1, borderTopColor: f.surfaces.rule, flexDirection: "row", gap: 8 }}>
            <AppLucideIcon name="circle-outline" size={14} color={f.surfaces.sub} />
            <AppText variant="caption" style={{ flex: 1, color: f.surfaces.sub }}>Anything outside this list is shown to you for approval before work starts.</AppText>
          </View>
        </View>
      ) : null}

      {summary.provider ? (
        <View style={{ minHeight: 50, paddingHorizontal: 14, borderRadius: 14, backgroundColor: f.soft(f.accents.a2), flexDirection: "row", alignItems: "center", gap: 10 }}>
          <AppLucideIcon name="person-outline" size={16} color={f.accents.a2} />
          <AppText variant="caption" style={{ flex: 1, color: f.surfaces.sub }}>Your technician's profile is shared as soon as the booking is confirmed.</AppText>
        </View>
      ) : null}

      <BotPrimaryButton label="Continue to schedule  →" onPress={onContinue} />
    </View>
  );
}
