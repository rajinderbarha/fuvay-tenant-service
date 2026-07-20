import React from "react";
import { StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { theme, gs } from "../../styles/theme";
import type { ChecklistItemView, ChecklistSectionView } from "../../types/ux05";
import { isItemComplete } from "../../lib/ux05/checklist";

export function ChecklistProgress({ percent }: { percent:number }) {
  return (
    <View testID="checklist-progress">
      <View style={[gs.row, { justifyContent:"space-between", marginBottom:5 }]}>
        <Text style={gs.label}>Progress</Text>
        <Text style={s.pct}>{percent}%</Text>
      </View>
      <View style={s.track}><View style={[s.fill, { width:`${percent}%` }]} /></View>
    </View>
  );
}

export function ChecklistSection({ section, onChange }: {
  section:ChecklistSectionView; onChange:(itemId:string, value:string) => void;
}) {
  return (
    <View style={[gs.card, { gap:12 }]} testID="checklist-section">
      <Text style={s.title}>{section.title}</Text>
      {section.items.map(item => <ChecklistItemRow key={item.id} item={item} onChange={v => onChange(item.id, v)} />)}
    </View>
  );
}

function ChecklistItemRow({ item, onChange }: { item:ChecklistItemView; onChange:(v:string) => void }) {
  const complete = isItemComplete(item);
  return (
    <View style={s.itemRow} accessibilityRole="none">
      <View style={[gs.row, { justifyContent:"space-between" }]}>
        <Text style={s.itemLabel}>{item.label}{item.required && <Text style={s.required}> *</Text>}</Text>
        {complete && <Text style={s.check}>✓</Text>}
      </View>
      {item.responseType === "pass_fail" ? (
        <View style={{ flexDirection:"row", gap:10, marginTop:6 }}>
          <TouchableOpacity accessibilityRole="button" accessibilityLabel={`${item.label} pass`}
            style={[s.pfBtn, item.value==="pass" && s.pfBtnActive]} onPress={() => onChange("pass")}>
            <Text style={s.pfText}>Pass</Text>
          </TouchableOpacity>
          <TouchableOpacity accessibilityRole="button" accessibilityLabel={`${item.label} fail`}
            style={[s.pfBtn, item.value==="fail" && s.pfBtnActiveFail]} onPress={() => onChange("fail")}>
            <Text style={s.pfText}>Fail</Text>
          </TouchableOpacity>
        </View>
      ) : item.responseType === "photo" ? (
        <Text style={s.photoHint}>{item.photoAttached ? "Photo attached" : "No photo yet"}</Text>
      ) : (
        <TextInput
          style={s.input}
          value={item.value ?? ""}
          onChangeText={onChange}
          keyboardType={item.responseType === "numeric" ? "numeric" : "default"}
          placeholder={item.responseType === "numeric" ? "Enter value" : "Enter notes"}
          placeholderTextColor={theme.colors.textTertiary}
          accessibilityLabel={item.label}
        />
      )}
    </View>
  );
}

const s = StyleSheet.create({
  title:     { fontSize:theme.font.size.lg, fontWeight:"700", color:theme.colors.textPrimary },
  itemRow:   { gap:4, paddingVertical:6, borderBottomWidth:1, borderBottomColor:theme.colors.border },
  itemLabel: { fontSize:theme.font.size.base, color:theme.colors.textPrimary },
  required:  { color:theme.colors.dangerText },
  check:     { color:theme.colors.successText, fontWeight:"800" },
  pfBtn:     { minWidth:64, minHeight:44, borderRadius:theme.radius.md, borderWidth:1, borderColor:theme.colors.border,
               alignItems:"center", justifyContent:"center", paddingHorizontal:14 },
  pfBtnActive:{ backgroundColor:theme.colors.successBg, borderColor:theme.colors.successBorder },
  pfBtnActiveFail:{ backgroundColor:theme.colors.dangerBg, borderColor:theme.colors.dangerBorder },
  pfText:    { fontSize:theme.font.size.sm, fontWeight:"600", color:theme.colors.textPrimary },
  photoHint: { fontSize:theme.font.size.sm, color:theme.colors.textTertiary },
  input:     { borderWidth:1, borderColor:theme.colors.border, borderRadius:theme.radius.md, padding:10,
               fontSize:theme.font.size.base, color:theme.colors.textPrimary, backgroundColor:theme.colors.surfaceSunken,
               minHeight:44 },
  pct:       { fontSize:theme.font.size.sm, fontWeight:"700", color:theme.colors.textPrimary },
  track:     { height:8, backgroundColor:theme.colors.border, borderRadius:4, overflow:"hidden" },
  fill:      { height:"100%", backgroundColor:theme.colors.success, borderRadius:4 },
});
