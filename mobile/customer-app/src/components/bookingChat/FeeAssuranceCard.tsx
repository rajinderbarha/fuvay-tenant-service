import React from "react";
import { View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useBotColors } from "./botTheme";
import { formatMoney } from "../../domain/money";
import { InspectionPricing } from "../../domain/servicePricing";
import { Money } from "../../domain/money";
import { BotText } from "./BotText";
import { BOT_GUTTER } from "./BotPrimitives";

export interface FeeAssuranceCardProps {
  inspection: InspectionPricing | null;
  /** Frozen surcharge for an emergency visit, shown BEFORE confirmation so
   * urgency is never a surprise line on the final bill. Null when the
   * booking is not an emergency, or the provider charges nothing extra. */
  emergencySurcharge: Money | null;
  /** Renders without its own card chrome so it can sit as a section inside
   * ReviewSheet's single scrolling column. */
  embedded?: boolean;
}

/**
 * The "no doubt about money" card, shown before the customer confirms.
 *
 * Every claim here is backed by real, verifiable behaviour:
 *  - the visit-fee credit is enforced in
 *    invoice_payment.direct_payments_service._expected_amount (approving the
 *    post-inspection estimate sets visit_fee_adjustment = -visit_fee);
 *  - the "only if the work costs more than the visit fee" limit is that same
 *    code's `work_amount > visit_fee` guard -- stated plainly rather than
 *    buried, because a customer whose repair is cheaper than the visit fee
 *    would otherwise feel misled;
 *  - "you only pay the visit fee" on decline is that function's
 *    `visit_fee_only` branch;
 *  - the emergency surcharge is the tenant's own configured rate, frozen on
 *    the booking at confirmation.
 *
 * The credit lines render ONLY when the backend asserted `visitFeePolicy`.
 * If it did not, this card shows the fee without a promise -- it never
 * invents an assurance the billing code would not honour.
 */
export function FeeAssuranceCard({ inspection, emergencySurcharge, embedded }: FeeAssuranceCardProps) {
  const BOT = useBotColors();
  if (!inspection && !emergencySurcharge) return null;

  const policy = inspection?.visitFeePolicy;
  const credited = !!policy?.creditedAgainstWork;

  return (
    <View
      style={
        embedded
          ? undefined
          : {
              marginLeft: BOT_GUTTER, borderRadius: 20, padding: 16,
              backgroundColor: BOT.successBg, borderWidth: 1, borderColor: BOT.successBorder,
            }
      }
    >
      <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
        <Ionicons name="shield-checkmark" size={18} color={BOT.success} />
        <BotText style={{ fontSize: 16, fontWeight: "700", color: BOT.textPrimary }}>
          What you&apos;ll pay
        </BotText>
      </View>

      {inspection ? (
        <View style={{ marginTop: 12, gap: 10 }}>
          <Line
            BOT={BOT}
            label="Inspection visit"
            value={formatMoney(inspection.visitFee)}
            strong
          />
          {credited ? (
            <>
              <Highlight BOT={BOT} icon="return-down-forward">
                This {formatMoney(inspection.visitFee)} is{" "}
                <BotText style={{ fontWeight: "700" }}>adjusted against your repair bill</BotText> if you
                go ahead with the work.
              </Highlight>
              <Muted BOT={BOT}>
                It is credited when you approve the technician&apos;s estimate, as long as the work
                costs more than the visit fee.
              </Muted>
              <Muted BOT={BOT}>
                If you decide not to go ahead, you pay only this visit fee — nothing more.
              </Muted>
            </>
          ) : null}
          <Line BOT={BOT} label="Repair cost" value="Quoted after inspection — you approve first" muted />
        </View>
      ) : null}

      {emergencySurcharge ? (
        <View style={{ marginTop: inspection ? 12 : 12, gap: 10 }}>
          <Line
            BOT={BOT}
            label="Emergency visit"
            value={`+${formatMoney(emergencySurcharge)}`}
            strong
          />
          <Muted BOT={BOT}>
            Your provider charges this for coming out at short notice. It is included in the total
            you see here, never added later.
          </Muted>
        </View>
      ) : null}

      <View
        style={{
          flexDirection: "row", alignItems: "center", gap: 8,
          marginTop: 14, paddingTop: 12, borderTopWidth: 1, borderTopColor: BOT.borderSubtle,
        }}
      >
        <Ionicons name="lock-closed" size={13} color={BOT.textTertiary} />
        <BotText style={{ flex: 1, fontSize: 13, color: BOT.textTertiary }}>
          No work starts until you approve the price.
        </BotText>
      </View>
    </View>
  );
}

function Line({
  BOT, label, value, strong, muted,
}: { BOT: ReturnType<typeof useBotColors>; label: string; value: string; strong?: boolean; muted?: boolean }) {
  return (
    <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
      <BotText style={{ fontSize: 15, color: BOT.textSecondary }}>{label}</BotText>
      <BotText
        style={{
          fontSize: strong ? 16 : 15,
          fontWeight: strong ? "700" : "400",
          color: muted ? BOT.textTertiary : BOT.textPrimary,
          flexShrink: 1, textAlign: "right",
        }}
      >
        {value}
      </BotText>
    </View>
  );
}

/** The one deliberately loud line -- this is the fact the customer most needs
 * to believe, so it gets the brand tint rather than body colour. */
function Highlight({
  BOT, icon, children,
}: { BOT: ReturnType<typeof useBotColors>; icon: React.ComponentProps<typeof Ionicons>["name"]; children: React.ReactNode }) {
  return (
    <View
      style={{
        flexDirection: "row", gap: 8, alignItems: "flex-start",
        backgroundColor: BOT.brandTint, borderRadius: 12, padding: 12,
      }}
    >
      <Ionicons name={icon} size={15} color={BOT.brand} style={{ marginTop: 2 }} />
      <BotText style={{ flex: 1, fontSize: 15, lineHeight: 21, color: BOT.textPrimary }}>{children}</BotText>
    </View>
  );
}

function Muted({ BOT, children }: { BOT: ReturnType<typeof useBotColors>; children: React.ReactNode }) {
  return <BotText style={{ fontSize: 13, lineHeight: 19, color: BOT.textTertiary }}>{children}</BotText>;
}
