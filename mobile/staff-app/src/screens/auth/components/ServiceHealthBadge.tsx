import React, { useEffect, useState } from "react";
import { View } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { AppText } from "../../../design-system/components/typography/AppText";
import { checkPublicHealth, PublicHealthStatus } from "../../../services/api/healthApi";

const LABEL: Record<PublicHealthStatus | "checking", string> = {
  checking: "Checking service status…",
  online: "Services operational",
  limited: "Limited service",
  unavailable: "Service unavailable",
};

/**
 * Optional public health indicator (Phase G spec section 1). Uses the
 * REAL public health endpoint (services/api/healthApi.ts, backed by
 * GET /v1/health) -- a failure here never exposes technical detail, it
 * only ever shows one of the three safe labels above.
 */
export function ServiceHealthBadge() {
  const { theme } = useTheme();
  const [status, setStatus] = useState<PublicHealthStatus | "checking">("checking");

  useEffect(() => {
    let mounted = true;
    const controller = new AbortController();
    checkPublicHealth(controller.signal).then(result => { if (mounted) setStatus(result); });
    return () => { mounted = false; controller.abort(); };
  }, []);

  const dotColor = status === "online" ? theme.colors.statusSuccess
    : status === "limited" ? theme.colors.statusWarning
    : status === "unavailable" ? theme.colors.statusDanger
    : theme.colors.textTertiary;

  return (
    <View
      accessibilityRole="text"
      accessibilityLabel={LABEL[status]}
      style={{
        flexDirection: "row", alignItems: "center", gap: 6, alignSelf: "center",
        paddingHorizontal: theme.spacing.sm, paddingVertical: 6,
        borderRadius: theme.radiusUsage.statusPill, backgroundColor: theme.colors.surfaceInteractive,
      }}
    >
      <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: dotColor }} />
      <AppText variant="labelStrong" color={status === "unavailable" ? "danger" : status === "limited" ? "warning" : "secondary"}>
        {LABEL[status]}
      </AppText>
    </View>
  );
}
