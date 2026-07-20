import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { theme, gs } from "../../styles/theme";
import type { JobMediaView } from "../../types/ux05";

const STATE_LABEL: Record<JobMediaView["uploadState"], string> = {
  draft:"Draft", uploading:"Uploading…", confirmed:"Uploaded", failed:"Failed — tap to retry",
};

/**
 * Media capture grid (workstream 19). Never renders storage keys, signed
 * URLs, bucket names, or credentials -- JobMediaView carries none of those
 * fields at all (see types/ux05.ts). An item is never labeled "Uploaded"
 * unless confirmedByBackend is true, even if uploadState optimistically
 * says "confirmed" -- this guards against the upload affordance lying.
 * API_CONTRACT_REQUIRED: no live media endpoint exists; add/remove act on
 * local state only.
 */
export function MediaCaptureGrid({ items, onAdd, onRemove }: {
  items:JobMediaView[]; onAdd:() => void; onRemove:(id:string) => void;
}) {
  return (
    <View style={[gs.card, { gap:10 }]} testID="media-capture-grid">
      <Text style={gs.label}>Media</Text>
      <View style={s.grid}>
        {items.map(m => (
          <View key={m.id} style={s.tile}>
            <Text style={s.tileIcon}>🖼</Text>
            <Text style={s.tileState}>
              {m.confirmedByBackend ? "Uploaded" : STATE_LABEL[m.uploadState]}
            </Text>
            {m.uploadState !== "confirmed" && (
              <TouchableOpacity onPress={() => onRemove(m.id)} accessibilityLabel="Remove photo">
                <Text style={s.remove}>✕</Text>
              </TouchableOpacity>
            )}
          </View>
        ))}
        <TouchableOpacity style={s.addTile} onPress={onAdd} accessibilityRole="button" accessibilityLabel="Add photo">
          <Text style={s.addIcon}>+</Text>
        </TouchableOpacity>
      </View>
      <Text style={s.mockNote}>MOCK_DESIGN_ONLY -- no live media endpoint wired yet; nothing is ever marked Uploaded before backend confirmation.</Text>
    </View>
  );
}

const s = StyleSheet.create({
  grid:     { flexDirection:"row", flexWrap:"wrap", gap:10 },
  tile:     { width:84, height:84, borderRadius:theme.radius.md, borderWidth:1, borderColor:theme.colors.border,
              alignItems:"center", justifyContent:"center", gap:2, backgroundColor:theme.colors.surfaceSunken },
  tileIcon: { fontSize:24 },
  tileState:{ fontSize:9, color:theme.colors.textTertiary, textAlign:"center" },
  remove:   { fontSize:12, color:theme.colors.dangerText, fontWeight:"800" },
  addTile:  { width:84, height:84, borderRadius:theme.radius.md, borderWidth:1, borderStyle:"dashed",
              borderColor:theme.colors.borderStrong, alignItems:"center", justifyContent:"center" },
  addIcon:  { fontSize:28, color:theme.colors.textTertiary },
  mockNote: { fontSize:theme.font.size.xs, color:theme.colors.textTertiary },
});
