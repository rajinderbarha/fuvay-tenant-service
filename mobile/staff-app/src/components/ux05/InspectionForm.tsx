import React from "react";
import { StyleSheet, Text, TextInput, View } from "react-native";
import { theme, gs } from "../../styles/theme";
import type { InspectionDraftView } from "../../types/ux05";

export function InspectionForm({ draft, onChange, readOnly }: {
  draft:InspectionDraftView; onChange:(field:keyof InspectionDraftView, value:string) => void; readOnly:boolean;
}) {
  return (
    <View style={[gs.card, { gap:12 }]} testID="inspection-form">
      <Field label="Customer Issue" value={draft.customerIssue} onChange={v => onChange("customerIssue", v)} readOnly={readOnly} />
      <Field label="Observations" value={draft.observations} onChange={v => onChange("observations", v)} readOnly={readOnly} multiline />
      <Field label="Recommended Work" value={draft.recommendedWork} onChange={v => onChange("recommendedWork", v)} readOnly={readOnly} multiline />
      <Field label="Customer-Visible Summary" value={draft.customerVisibleSummary} onChange={v => onChange("customerVisibleSummary", v)} readOnly={readOnly} multiline />
      <Field label="Internal Note (not shown to customer)" value={draft.internalNote} onChange={v => onChange("internalNote", v)} readOnly={readOnly} multiline />
    </View>
  );
}

function Field({ label, value, onChange, readOnly, multiline }: {
  label:string; value:string; onChange:(v:string) => void; readOnly:boolean; multiline?:boolean;
}) {
  return (
    <View>
      <Text style={s.label}>{label}</Text>
      {readOnly ? (
        <Text style={s.readOnlyValue}>{value || "—"}</Text>
      ) : (
        <TextInput
          style={[s.input, multiline && s.multiline]}
          value={value} onChangeText={onChange} multiline={multiline}
          placeholderTextColor={theme.colors.textTertiary}
          accessibilityLabel={label}
        />
      )}
    </View>
  );
}

const s = StyleSheet.create({
  label:        { fontSize:theme.font.size.sm, fontWeight:"700", color:theme.colors.textSecondary, marginBottom:4 },
  input:        { borderWidth:1, borderColor:theme.colors.border, borderRadius:theme.radius.md, padding:10,
                  fontSize:theme.font.size.base, color:theme.colors.textPrimary, backgroundColor:theme.colors.surfaceSunken },
  multiline:    { minHeight:70, textAlignVertical:"top" },
  readOnlyValue:{ fontSize:theme.font.size.base, color:theme.colors.textPrimary },
});
