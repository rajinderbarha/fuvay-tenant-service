import React, { useState } from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppButton } from "../AppButton";
import { PasswordField } from "../auth/PasswordField";
import { useChangePasswordMutation } from "../../api/customerSecurity/useChangePasswordMutation";
import { DomainError } from "../../domain/errors";

export interface ChangePasswordCardProps {
  onDone: () => void;
  onCancel: () => void;
}

function validate(current: string, next: string, confirm: string): string | null {
  if (!current) return "Enter your current password.";
  if (next.length < 8) return "New password must be at least 8 characters.";
  if (next !== confirm) return "New password and confirmation do not match.";
  if (next === current) return "New password must be different from your current password.";
  return null;
}

/** Inline focused form (spec section 6 allows "a separate focused screen
 * or secure modal" -- kept inline within the Security screen's own
 * scroll, matching the approved design's single-screen flow). Server is
 * authoritative for final validation; this is progressive disclosure
 * only. Clears sensitive state on success; preserves nothing sensitive
 * on failure (only the non-sensitive screen-error copy). */
export function ChangePasswordCard({ onDone, onCancel }: ChangePasswordCardProps) {
  const { theme } = useTheme();
  const mutation = useChangePasswordMutation();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [touched, setTouched] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const fieldError = touched ? validate(current, next, confirm) : null;

  async function handleSubmit() {
    setServerError(null);
    setTouched(true);
    if (validate(current, next, confirm)) return;
    try {
      await mutation.mutateAsync({ current_password: current, new_password: next, confirm_password: confirm });
      setCurrent(""); setNext(""); setConfirm(""); setTouched(false);
      onDone();
    } catch (err) {
      // Never preserve password values after any attempt -- only
      // non-sensitive error copy survives (spec section 13).
      setCurrent(""); setNext(""); setConfirm("");
      setServerError(err instanceof DomainError ? err.diagnostic : "Couldn't change your password.");
    }
  }

  return (
    <View style={{ gap: theme.spacing.sm }}>
      <PasswordField label="Current password" value={current} onChangeText={t => { setCurrent(t); setServerError(null); }} autoComplete="current-password" disabled={mutation.isPending} />
      <PasswordField label="New password" value={next} onChangeText={t => { setNext(t); setServerError(null); }} autoComplete="new-password" disabled={mutation.isPending} />
      <PasswordField label="Confirm new password" value={confirm} onChangeText={t => { setConfirm(t); setServerError(null); }} autoComplete="new-password" disabled={mutation.isPending} error={fieldError ?? undefined} />
      {serverError ? <AppText variant="bodySmall" color="danger">{serverError}</AppText> : null}
      <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
        <View style={{ flex: 1 }}>
          <AppButton label="Cancel" tone="secondary" onPress={onCancel} disabled={mutation.isPending} fullWidth />
        </View>
        <View style={{ flex: 1 }}>
          <AppButton
            label="Update password" onPress={handleSubmit}
            loading={mutation.isPending}
            disabled={!current || !next || !confirm}
            fullWidth
          />
        </View>
      </View>
      {mutation.isPending ? <AppText variant="caption" color="secondary" align="center">Updating password…</AppText> : null}
    </View>
  );
}
