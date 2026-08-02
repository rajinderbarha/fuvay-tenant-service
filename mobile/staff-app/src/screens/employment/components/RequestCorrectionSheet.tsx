import React, { useState } from "react";
import { View, ScrollView } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { BottomSheet } from "../../../design-system/components/overlays/BottomSheet";
import { Heading } from "../../../design-system/components/typography/Heading";
import { AppText } from "../../../design-system/components/typography/AppText";
import { SelectField } from "../../../design-system/components/forms/SelectField";
import { TextField } from "../../../design-system/components/forms/TextField";
import { TextArea } from "../../../design-system/components/forms/TextArea";
import { PrimaryButton, SecondaryButton } from "../../../design-system/components/actions/Buttons";
import { InlineAlert } from "../../../design-system/components/feedback/Banner";
import { CorrectionFieldKey } from "../../../services/employment/types";

const FIELD_LABELS: Record<CorrectionFieldKey, string> = {
  designation: "Designation",
  reports_to: "Reporting manager",
  service_group: "Assigned service group",
  job_type: "Assigned job type",
  skill: "Skill / certification",
  service_area: "Service area",
  joined_at: "Joined date",
};

const FIELD_ORDER: CorrectionFieldKey[] = ["designation", "reports_to", "service_group", "job_type", "skill", "service_area", "joined_at"];

/** Structured "Request employment correction" flow (spec section 10). The
 * technician can only pick from a fixed correctable-field allowlist -- never
 * tenant identity, platform user id, audit records, security state, raw
 * permission codes, or another employee's data. */
export function RequestCorrectionSheet({ visible, onClose, currentValues, submitting, error, onSubmit }: {
  visible: boolean;
  onClose: () => void;
  currentValues: Partial<Record<CorrectionFieldKey, string | null>>;
  submitting: boolean;
  error: string | null;
  onSubmit: (fieldKey: CorrectionFieldKey, requestedValue: string, reason: string) => Promise<{ ok: boolean }>;
}) {
  const { theme } = useTheme();
  const [pickingField, setPickingField] = useState(false);
  const [fieldKey, setFieldKey] = useState<CorrectionFieldKey | null>(null);
  const [requestedValue, setRequestedValue] = useState("");
  const [reason, setReason] = useState("");
  const [done, setDone] = useState(false);

  const reset = () => { setFieldKey(null); setRequestedValue(""); setReason(""); setDone(false); };
  const handleClose = () => { reset(); onClose(); };

  const handleSubmit = async () => {
    if (!fieldKey || !requestedValue.trim() || !reason.trim()) return;
    const result = await onSubmit(fieldKey, requestedValue.trim(), reason.trim());
    if (result.ok) setDone(true);
  };

  return (
    <BottomSheet visible={visible} onClose={handleClose} dismissible={!submitting}>
      <ScrollView contentContainerStyle={{ paddingBottom: theme.spacing.xl }}>
        <Heading level="medium">Request employment correction</Heading>
        {done ? (
          <View style={{ marginTop: theme.spacing.base }}>
            <InlineAlert tone="success" title="Request submitted" message="Your business will review this and you'll be notified of the decision." />
            <View style={{ height: theme.spacing.base }} />
            <PrimaryButton label="Done" onPress={handleClose} fullWidth />
          </View>
        ) : (
          <View style={{ marginTop: theme.spacing.base, gap: theme.spacing.sm }}>
            <SelectField
              label="Field requiring correction"
              displayValue={fieldKey ? FIELD_LABELS[fieldKey] : undefined}
              onPress={() => setPickingField(v => !v)}
              required
            />
            {pickingField ? (
              <View>
                {FIELD_ORDER.map(key => (
                  <SecondaryButton
                    key={key}
                    label={FIELD_LABELS[key]}
                    onPress={() => { setFieldKey(key); setRequestedValue(""); setPickingField(false); }}
                    style={{ marginBottom: theme.spacing.xs }}
                  />
                ))}
              </View>
            ) : null}

            {fieldKey ? (
              <>
                <TextField label="Current value" value={currentValues[fieldKey] ?? "—"} editable={false} />
                <TextField label="Requested correction" value={requestedValue} onChangeText={setRequestedValue} />
                <TextArea label="Reason" value={reason} onChangeText={setReason} minLines={3} />
              </>
            ) : null}

            {error ? <InlineAlert tone="danger" title="Couldn't submit" message={error} /> : null}

            <View style={{ flexDirection: "row", gap: theme.spacing.sm, marginTop: theme.spacing.sm }}>
              <SecondaryButton label="Cancel" onPress={handleClose} />
              <PrimaryButton
                label="Submit"
                onPress={handleSubmit}
                loading={submitting}
                disabled={!fieldKey || !requestedValue.trim() || !reason.trim()}
              />
            </View>
          </View>
        )}
      </ScrollView>
    </BottomSheet>
  );
}
