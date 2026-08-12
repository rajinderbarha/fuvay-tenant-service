import React, { useState } from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { CustomerDirectPayment, CustomerHandover } from "../../api/contracts/customerClosure";
import { AppCard } from "../AppCard";
import { AppText } from "../AppText";
import { AppButton } from "../AppButton";
import { Icon } from "../Icon";

interface Props {
  handover: CustomerHandover | null;
  payment: CustomerDirectPayment | null;
  busy: boolean;
  failed: boolean;
  onAcknowledge: () => void;
  onConfirmPayment: () => void;
  onReportNotPaid: () => void;
}

export function CompletionConfirmationCard({ handover, payment, busy, failed, onAcknowledge, onConfirmPayment, onReportNotPaid }: Props) {
  const { theme } = useTheme();
  const [reportingIssue, setReportingIssue] = useState(false);
  if (!handover || (handover.status === "not_requested" && !payment)) return null;

  const needsHandover = handover.can_acknowledge;
  const issueReported = !!payment?.customer_action && !payment.customer_confirmed;
  const needsPayment = !!payment && !payment.customer_confirmed && !payment.customer_action
    && (payment.status === "awaiting_customer" || payment.status === "mismatched");
  const complete = handover.status === "acknowledged" && !!payment?.customer_confirmed;

  return (
    <AppCard style={{ gap: theme.spacing.sm, borderColor: needsHandover || needsPayment ? theme.colors.brandPrimary : theme.colors.borderDefault }}>
      <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start" }}>
        <Icon name={complete ? "checkmark-circle-outline" : "shield-checkmark-outline"} size="standard" color={complete ? theme.colors.statusSuccess : theme.colors.brandPrimaryStrong} decorative />
        <View style={{ flex: 1, gap: theme.spacing.xxs }}>
          <AppText variant="bodyStrong" accessibilityRole="header">
            {needsHandover ? "Confirm service handover" : needsPayment ? "Confirm your direct payment" : issueReported ? "Payment issue reported" : complete ? "Service closure confirmed" : "Waiting for payment record"}
          </AppText>
          <AppText variant="bodySmall" color="secondary">
            {needsHandover
              ? "The technician has submitted the completion proof. Confirm that the completed work was handed over to you."
              : needsPayment && payment
                ? `${payment.provider_business ?? "The provider"} recorded ${payment.currency} ${payment.service_amount} paid by ${payment.method}. ServiceOS did not collect this money.`
                : issueReported
                  ? "Your payment issue was sent to the provider. The job cannot close until it is resolved."
                : complete
                  ? "Your handover and payment confirmations are complete. The provider can now close the job."
                  : "Handover is confirmed. The technician still needs to record the direct payment."}
          </AppText>
        </View>
      </View>
      {failed ? <AppText variant="bodySmall" style={{ color: theme.colors.statusDanger }}>We couldn't save that confirmation. Please try again.</AppText> : null}
      {needsHandover ? (
        <AppButton label="Confirm handover" fullWidth loading={busy} onPress={onAcknowledge} />
      ) : needsPayment && payment ? (
        <View style={{ gap: theme.spacing.xs }}>
          <AppButton label={`Yes, I paid ${payment.currency} ${payment.service_amount}`} fullWidth loading={busy} onPress={onConfirmPayment} />
          {reportingIssue ? (
            <View style={{ gap: theme.spacing.xs }}>
              <AppText variant="bodySmall" style={{ color: theme.colors.statusDanger }}>
                Report this only if you did not pay the amount shown. The provider will be asked to resolve the mismatch before closing the job.
              </AppText>
              <AppButton label="Confirm payment issue" tone="destructive" fullWidth disabled={busy} onPress={onReportNotPaid} />
              <AppButton label="Go back" tone="secondary" fullWidth disabled={busy} onPress={() => setReportingIssue(false)} />
            </View>
          ) : (
            <AppButton label="I did not make this payment" tone="destructive" fullWidth disabled={busy} onPress={() => setReportingIssue(true)} />
          )}
        </View>
      ) : null}
    </AppCard>
  );
}
