import React, { useState } from "react";
import { View } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { useTheme } from "../../../design-system/themes";
import { AppText } from "../../../design-system/components/typography/AppText";
import { Icon } from "../../../design-system/components/Icon";
import { TextField } from "../../../design-system/components/forms/TextField";
import { TextArea } from "../../../design-system/components/forms/TextArea";
import { Switch } from "../../../design-system/components/forms/Switch";
import { PrimaryButton } from "../../../design-system/components/actions/Buttons";
import { AttachmentThumbnail } from "../../../design-system/components/data-display/AttachmentThumbnail";
import { LoadingSpinner } from "../../../design-system/components/feedback/Loading";
import { SelectChips } from "./SelectChips";
import { ChecklistItemDTO } from "../../../services/inspection/types";

export interface ChecklistItemRowProps {
  item: ChecklistItemDTO;
  disabled: boolean;
  saving: boolean;
  uploading: boolean;
  onSave: (responseValue: Record<string, unknown> | null, evidence: { file_id: string }[] | null) => void;
  onPickEvidence: () => Promise<{ ok: boolean; fileId?: string }>;
}

function StatusIcon({ item }: { item: ChecklistItemDTO }) {
  const { theme } = useTheme();
  const answered = item.response && item.response.response_value !== null;
  if (!item.is_required) return <Icon name="ellipse-outline" size="compact" color={theme.colors.textTertiary} decorative />;
  if (answered) return <Icon name="checkmark-circle" size="compact" color={theme.colors.statusSuccess} decorative />;
  return <Icon name="ellipse" size="compact" color={theme.colors.statusWarning} decorative />;
}

/**
 * Renders the correct inline editor for whatever `item_type` the backend
 * checklist definition returns (spec section 5) -- no client-side item
 * type inference or hardcoded universal question set.
 */
export function ChecklistItemRow({ item, disabled, saving, uploading, onSave, onPickEvidence }: ChecklistItemRowProps) {
  const { theme } = useTheme();
  const existingValue = item.response?.response_value ?? {};
  const [text, setText] = useState<string>(typeof existingValue.value === "string" ? existingValue.value : "");
  const [numberText, setNumberText] = useState<string>(existingValue.value !== undefined && existingValue.value !== null ? String(existingValue.value) : "");
  const evidence = item.response?.evidence ?? [];

  const savingThis = saving;

  return (
    <View style={{ paddingVertical: theme.spacing.base, borderBottomWidth: 1, borderBottomColor: theme.colors.borderSubtle }}>
      <View style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.sm, marginBottom: theme.spacing.xs }}>
        <StatusIcon item={item} />
        <View style={{ flex: 1 }}>
          <AppText variant="body">{item.label}</AppText>
          {item.help_text ? <AppText variant="caption" color="tertiary">{item.help_text}</AppText> : null}
        </View>
        {savingThis ? <LoadingSpinner /> : item.is_required ? <AppText variant="caption" color="warning">Required</AppText> : null}
      </View>

      <View style={{ marginTop: theme.spacing.xs }}>
        {(item.item_type === "YES_NO" || item.item_type === "CHECKBOX") ? (
          <Switch
            label={existingValue.value === "yes" || existingValue.value === true ? "Yes" : "No"}
            value={existingValue.value === "yes" || existingValue.value === true}
            onChange={v => onSave({ value: v ? "yes" : "no" }, null)}
            disabled={disabled}
          />
        ) : item.item_type === "SHORT_TEXT" ? (
          <TextField
            value={text} onChangeText={setText} editable={!disabled}
            placeholder="Enter a response…"
            onBlur={() => text.trim() && onSave({ value: text.trim() }, null)}
          />
        ) : item.item_type === "LONG_TEXT" ? (
          <TextArea
            value={text} onChangeText={setText} editable={!disabled}
            placeholder="Enter findings…"
            onBlur={() => text.trim() && onSave({ value: text.trim() }, null)}
          />
        ) : (item.item_type === "NUMBER" || item.item_type === "MEASUREMENT") ? (
          <TextField
            value={numberText} onChangeText={setNumberText} editable={!disabled}
            keyboardType="numeric" placeholder={item.measurement_unit ? `Value (${item.measurement_unit})` : "Value"}
            onBlur={() => numberText.trim() && onSave({ value: Number(numberText) }, null)}
          />
        ) : (item.item_type === "SINGLE_SELECT" || item.item_type === "MULTI_SELECT") ? (
          <SelectChips
            options={item.select_options ?? []}
            selected={Array.isArray(existingValue.values) ? (existingValue.values as string[]) : (existingValue.value ? [String(existingValue.value)] : [])}
            multi={item.item_type === "MULTI_SELECT"}
            disabled={disabled}
            onToggle={(val) => {
              if (item.item_type === "MULTI_SELECT") {
                const current = Array.isArray(existingValue.values) ? (existingValue.values as string[]) : [];
                const next = current.includes(val) ? current.filter(v => v !== val) : [...current, val];
                onSave({ values: next }, null);
              } else {
                onSave({ value: val }, null);
              }
            }}
          />
        ) : (item.item_type === "PHOTO" || item.item_type === "DOCUMENT") ? (
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.sm }}>
            {evidence.map(f => <AttachmentThumbnail key={f.file_id} label="Evidence" />)}
            {!disabled ? (
              uploading ? <LoadingSpinner /> : (
                <AttachmentThumbnail label="Add photo" onPress={async () => {
                  const result = await onPickEvidence();
                  if (result.ok && result.fileId) {
                    onSave(item.response?.response_value ?? { attached: true }, [...evidence.map(e => ({ file_id: e.file_id })), { file_id: result.fileId }]);
                  }
                }} />
              )
            ) : null}
          </View>
        ) : (
          // SIGNATURE -- no capture UI built this phase (disclosed PARTIAL in the completion report).
          <AppText variant="caption" color="tertiary">Signature capture is not available in this version.</AppText>
        )}
      </View>

      {item.evidence_required && evidence.length < Math.max(item.min_evidence_count, 1) ? (
        <AppText variant="caption" color="warning" style={{ marginTop: theme.spacing.xs }}>
          Minimum {Math.max(item.min_evidence_count, 1)} photo{item.min_evidence_count > 1 ? "s" : ""} required
        </AppText>
      ) : null}
    </View>
  );
}
