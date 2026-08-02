import React, { useState } from "react";
import { View, ScrollView } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { BottomSheet } from "../../../design-system/components/overlays/BottomSheet";
import { Heading } from "../../../design-system/components/typography/Heading";
import { AppText } from "../../../design-system/components/typography/AppText";
import { Switch } from "../../../design-system/components/forms/Switch";
import { TextField } from "../../../design-system/components/forms/TextField";
import { PrimaryButton, SecondaryButton } from "../../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../../design-system/components/feedback/Banner";
import { QuietHoursDTO } from "../../../services/notifications/preferencesTypes";

const TIME_RE = /^([01]\d|2[0-3]):[0-5]\d$/;

/** Quiet Hours (spec section 7). Overnight windows (e.g. 22:00-07:00) are
 * evaluated SERVER-SIDE (mobile_notification_preferences_service.py::
 * is_within_quiet_hours) -- this sheet only collects/validates input, it
 * never decides delivery locally. */
export function QuietHoursSheet({ visible, onClose, quietHours, saving, onSave }: {
  visible: boolean; onClose: () => void; quietHours: QuietHoursDTO;
  saving: boolean;
  onSave: (enabled: boolean, start: string | null, end: string | null) => void;
}) {
  const { theme } = useTheme();
  const [enabled, setEnabled] = useState(quietHours.enabled);
  const [start, setStart] = useState(quietHours.start_local_time ?? "22:00");
  const [end, setEnd] = useState(quietHours.end_local_time ?? "07:00");

  const validTimes = !enabled || (TIME_RE.test(start) && TIME_RE.test(end));

  return (
    <BottomSheet visible={visible} onClose={onClose} dismissible={!saving}>
      <ScrollView contentContainerStyle={{ paddingBottom: theme.spacing.xl }}>
        <Heading level="medium">Quiet hours</Heading>
        <View style={{ marginTop: theme.spacing.base }}>
          <Switch label="Enable quiet hours" value={enabled} onChange={setEnabled} accessibilityLabel="Enable quiet hours" />
        </View>
        {enabled ? (
          <View style={{ gap: theme.spacing.sm, marginTop: theme.spacing.sm }}>
            <TextField label="Start time (HH:MM)" value={start} onChangeText={setStart} placeholder="22:00" />
            <TextField label="End time (HH:MM)" value={end} onChangeText={setEnd} placeholder="07:00" />
            {!validTimes ? <InlineAlert tone="danger" message="Enter valid times in 24-hour HH:MM format." /> : null}
          </View>
        ) : null}
        <AppText variant="caption" color="tertiary" style={{ marginTop: theme.spacing.base }}>
          Timezone: {quietHours.timezone}. Critical job and security alerts can bypass quiet hours.
        </AppText>
        <View style={{ flexDirection: "row", gap: theme.spacing.sm, marginTop: theme.spacing.base }}>
          <SecondaryButton label="Cancel" onPress={onClose} />
          <PrimaryButton
            label="Save"
            loading={saving}
            disabled={!validTimes}
            onPress={() => onSave(enabled, enabled ? start : quietHours.start_local_time, enabled ? end : quietHours.end_local_time)}
          />
        </View>
      </ScrollView>
    </BottomSheet>
  );
}
