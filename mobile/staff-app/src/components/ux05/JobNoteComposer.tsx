import React, { useState } from "react";
import { StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { theme, gs } from "../../styles/theme";
import type { JobNoteView } from "../../types/ux05";

const VISIBILITY_LABEL: Record<JobNoteView["visibility"], string> = {
  internal: "Internal (tenant staff only)", technician: "Technician note", customer_visible: "Customer-visible",
};

/**
 * Job notes composer + list (workstream 18). Distinguishes internal /
 * technician / customer_visible notes explicitly in both composition
 * (a visibility picker, defaulting to the least-exposed option) and
 * display (a visible label on every note) -- an internal note can never
 * silently render as customer-visible. API_CONTRACT_REQUIRED: no live
 * notes endpoint exists; composing appends to local state only.
 */
export function JobNoteComposer({ notes, onAdd }: { notes:JobNoteView[]; onAdd:(text:string, visibility:JobNoteView["visibility"]) => void }) {
  const [text, setText] = useState("");
  const [visibility, setVisibility] = useState<JobNoteView["visibility"]>("technician");

  function submit() {
    if (!text.trim()) return;
    onAdd(text.trim(), visibility);
    setText("");
  }

  return (
    <View style={[gs.card, { gap:10 }]} testID="job-note-composer">
      <Text style={gs.label}>Notes</Text>
      {notes.map(n => (
        <View key={n.id} style={s.note}>
          <Text style={s.visibilityTag}>{VISIBILITY_LABEL[n.visibility]}</Text>
          <Text style={s.noteText}>{n.text}</Text>
        </View>
      ))}
      <View style={{ flexDirection:"row", gap:8 }}>
        {(Object.keys(VISIBILITY_LABEL) as JobNoteView["visibility"][]).map(v => (
          <TouchableOpacity key={v} onPress={() => setVisibility(v)}
            style={[s.visBtn, visibility===v && s.visBtnActive]}>
            <Text style={s.visBtnText}>{VISIBILITY_LABEL[v].split(" ")[0]}</Text>
          </TouchableOpacity>
        ))}
      </View>
      <TextInput style={s.input} value={text} onChangeText={setText} multiline
        placeholder="Add a note…" placeholderTextColor={theme.colors.textTertiary} accessibilityLabel="Add note" />
      <TouchableOpacity style={s.submitBtn} onPress={submit} accessibilityRole="button"><Text style={s.submitText}>Add Note</Text></TouchableOpacity>
      <Text style={s.mockNote}>MOCK_DESIGN_ONLY -- no live job-notes endpoint wired yet.</Text>
    </View>
  );
}

const s = StyleSheet.create({
  note:         { gap:2, paddingVertical:6, borderBottomWidth:1, borderBottomColor:theme.colors.border },
  visibilityTag:{ fontSize:theme.font.size.xs, fontWeight:"700", color:theme.colors.accent, textTransform:"uppercase" },
  noteText:     { fontSize:theme.font.size.sm, color:theme.colors.textPrimary },
  visBtn:       { paddingHorizontal:10, paddingVertical:6, borderRadius:theme.radius.sm, borderWidth:1, borderColor:theme.colors.border },
  visBtnActive: { backgroundColor:theme.colors.accentLight, borderColor:theme.colors.accent },
  visBtnText:   { fontSize:theme.font.size.xs, fontWeight:"600", color:theme.colors.textPrimary },
  input:        { borderWidth:1, borderColor:theme.colors.border, borderRadius:theme.radius.md, padding:10,
                  fontSize:theme.font.size.base, color:theme.colors.textPrimary, backgroundColor:theme.colors.surfaceSunken, minHeight:44 },
  submitBtn:    { height:40, borderRadius:theme.radius.md, backgroundColor:theme.colors.brand, alignItems:"center", justifyContent:"center" },
  submitText:   { color:"#fff", fontWeight:"700" },
  mockNote:     { fontSize:theme.font.size.xs, color:theme.colors.textTertiary },
});
