import React, { useEffect, useRef, useState } from "react";
import { AccessibilityInfo } from "react-native";
import { AppText } from "../AppText";

export interface ResendCountdownProps {
  /** Backend-issued expiry instant for the resend cooldown -- NEVER a
   * locally-invented duration (spec section 10: "Do not hardcode 00:28;
   * that value is visual-design sample content only"). Passing a fixed
   * duration client-side would let a customer's countdown drift from the
   * server's real rate-limit window. */
  cooldownUntil: Date;
  onCooldownElapsed?: () => void;
}

function formatRemaining(ms: number): string {
  const totalSeconds = Math.max(0, Math.ceil(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

export function ResendCountdown({ cooldownUntil, onCooldownElapsed }: ResendCountdownProps) {
  const [remainingMs, setRemainingMs] = useState(() => cooldownUntil.getTime() - Date.now());
  const announcedElapsed = useRef(false);

  useEffect(() => {
    announcedElapsed.current = false;
    const interval = setInterval(() => {
      const next = cooldownUntil.getTime() - Date.now();
      setRemainingMs(next);
      if (next <= 0 && !announcedElapsed.current) {
        announcedElapsed.current = true;
        AccessibilityInfo.announceForAccessibility("You can now resend the code.");
        onCooldownElapsed?.();
        clearInterval(interval);
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [cooldownUntil, onCooldownElapsed]);

  if (remainingMs <= 0) return null;

  return (
    <AppText variant="bodySmall" color="secondary">
      {`Resend code in ${formatRemaining(remainingMs)}`}
    </AppText>
  );
}
