import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { theme } from "../../styles/theme";
import type { NotificationView } from "../../types/ux05";

const PRIORITY_COLOR: Record<string,string> = {
  high: theme.colors.danger, medium: theme.colors.warning, low: theme.colors.brand,
};

export function NotificationCard({ item, onPress }: { item:NotificationView; onPress:() => void }) {
  const n = item.notification;
  const unread = n.read_status !== "read";
  return (
    <TouchableOpacity style={[s.row, unread && s.rowUnread]} activeOpacity={0.85} onPress={onPress} testID="notification-card"
      accessibilityRole="button"
      accessibilityLabel={`${unread ? "Unread. " : ""}${n.title}`}
      accessibilityState={{ selected: unread }}>
      {/* status-beyond-color: unread is also conveyed in the accessibility
          label text above, not solely by the dot's fill color */}
      <View style={[s.dot, { backgroundColor: unread ? PRIORITY_COLOR[item.priority] : "transparent", borderColor:PRIORITY_COLOR[item.priority] }]} />
      <View style={{ flex:1 }}>
        <Text style={[s.title, unread && s.titleUnread]}>{n.title}</Text>
        {n.body && <Text style={s.body} numberOfLines={2}>{n.body}</Text>}
      </View>
    </TouchableOpacity>
  );
}

const s = StyleSheet.create({
  row:        { flexDirection:"row", alignItems:"flex-start", gap:12, padding:14, backgroundColor:theme.colors.surface },
  rowUnread:  { backgroundColor:theme.colors.surfaceSunken },
  dot:        { width:10, height:10, borderRadius:5, borderWidth:1.5, marginTop:5 },
  title:      { fontSize:theme.font.size.base, fontWeight:"600", color:theme.colors.textPrimary },
  titleUnread:{ fontWeight:"800" },
  body:       { fontSize:theme.font.size.sm, color:theme.colors.textSecondary, marginTop:3 },
});
