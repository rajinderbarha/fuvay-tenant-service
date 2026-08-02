import React, { useEffect, useState } from "react";
import { View } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { Card } from "../../../design-system/components/foundation/Layout";
import { AppText } from "../../../design-system/components/typography/AppText";
import { NumericText } from "../../../design-system/components/typography/NumericText";
import { SecondaryButton } from "../../../design-system/components/actions/Buttons";
import { WorkSessionDTO } from "../../../services/workExecution/types";

function formatElapsed(totalSeconds: number): string {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = Math.floor(totalSeconds % 60);
  return [h, m, s].map(n => String(n).padStart(2, "0")).join(":");
}

export interface WorkSessionCardProps {
  session: WorkSessionDTO | null;
  onPause: () => void;
  onResume: () => void;
  disabled?: boolean;
}

/**
 * Server-authoritative elapsed time (spec section 7): the on-screen ticking
 * clock is presentation only, derived from `accumulated_seconds` (frozen at
 * the last pause/refetch) plus a local 1s ticker while the session is
 * active -- reconstructed from backend data on every load/refetch, never
 * trusted across an app restart on its own.
 */
export function WorkSessionCard({ session, onPause, onResume, disabled }: WorkSessionCardProps) {
  const { theme } = useTheme();
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (session?.state !== "active") return;
    const interval = setInterval(() => setTick(t => t + 1), 1000);
    return () => clearInterval(interval);
  }, [session?.state]);

  if (!session) return null;

  const displaySeconds = session.state === "active" ? session.accumulated_seconds + tick : session.accumulated_seconds;

  return (
    <Card>
      <AppText variant="label" color="warning">Work session</AppText>
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: theme.spacing.xs }}>
        <NumericText size="large" accessibilityLabel={`Elapsed time ${formatElapsed(displaySeconds)}`}>
          {formatElapsed(displaySeconds)}
        </NumericText>
        {session.state === "active" ? (
          <SecondaryButton label="Pause" onPress={onPause} disabled={disabled} />
        ) : session.state === "paused" ? (
          <SecondaryButton label="Resume" onPress={onResume} disabled={disabled} />
        ) : null}
      </View>
      <AppText variant="caption" color="tertiary">
        {session.started_at ? `Started ${new Date(session.started_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}` : ""}
        {session.state === "paused" && session.pause_reason ? ` · Paused: ${session.pause_reason}` : ""}
      </AppText>
    </Card>
  );
}
