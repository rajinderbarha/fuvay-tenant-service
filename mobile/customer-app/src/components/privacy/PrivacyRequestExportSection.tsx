import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppButton } from "../AppButton";
import { PrivacyRequestExport } from "../../domain/privacyData";
import { ServerTimestamp, toDisplayDate } from "../../domain/dates";

function formatDateTime(timestamp: ServerTimestamp) {
  return toDisplayDate(timestamp).toLocaleString(undefined, {
    day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit",
  });
}

export interface PrivacyRequestExportSectionProps {
  exportInfo: PrivacyRequestExport;
  onDownload: () => void;
  downloadPending: boolean;
  downloadError: string | null;
  offline: boolean;
}

/** Only the real export states the backend actually produces
 * (`ComplianceExport.status`: generating/ready/downloaded/expired) --
 * "failed" is a modeled backend value with no current retry contract, so
 * Retry is intentionally not offered (spec section 9: "Show Retry only if
 * the backend supports retry"). */
export function PrivacyRequestExportSection({
  exportInfo, onDownload, downloadPending, downloadError, offline,
}: PrivacyRequestExportSectionProps) {
  const { theme } = useTheme();

  if (exportInfo.isExpired || exportInfo.status === "expired") {
    return (
      <AppCard style={{ gap: theme.spacing.xs }}>
        <AppText variant="bodyStrong">Your export has expired</AppText>
        <AppText variant="bodySmall" color="secondary">
          For your security, export links expire after a few days. Submit a new export request to get a fresh copy.
        </AppText>
      </AppCard>
    );
  }

  if (exportInfo.status === "ready" || exportInfo.status === "downloaded") {
    const alreadyDownloaded = exportInfo.status === "downloaded";
    return (
      <AppCard style={{ gap: theme.spacing.sm }}>
        <AppText variant="bodyStrong">{alreadyDownloaded ? "Your data has been downloaded" : "Your data is ready"}</AppText>
        {exportInfo.expiresAt ? (
          <AppText variant="bodySmall" color="secondary">Available until {formatDateTime(exportInfo.expiresAt)}</AppText>
        ) : null}
        {downloadError ? <AppText variant="bodySmall" color="danger">{downloadError}</AppText> : null}
        <AppButton
          label={alreadyDownloaded ? "Download again" : "Download your data"} tone={alreadyDownloaded ? "secondary" : "primary"}
          onPress={onDownload} loading={downloadPending} disabled={offline} fullWidth
        />
      </AppCard>
    );
  }

  return (
    <AppCard style={{ gap: theme.spacing.xs }}>
      <AppText variant="bodyStrong">Preparing your data</AppText>
      <AppText variant="bodySmall" color="secondary">We're putting your export together. Check back soon.</AppText>
    </AppCard>
  );
}
