import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { theme } from "../../styles/theme";
import type { ActionPermissionView } from "../../types/ux05";
import { ACTION_LABEL, ACTION_VARIANT } from "../../lib/transitions";

/**
 * Sticky primary-action bar for Current Job mode / job detail. Only ever
 * renders repository-backed actions from ActionPermissionView -- never
 * invents a skip-ahead or reverse transition. Disabled + reason shown when
 * offline (status transitions are always online-required).
 */
export function NextActionBar({ action, onPress, offline }: {
  action: ActionPermissionView | null; onPress:() => void; offline:boolean;
}) {
  if (!action) return null;
  const variant = ACTION_VARIANT[action.action] ?? "primary";
  const disabled = !action.available || offline;
  return (
    <View style={s.bar} testID="next-action-bar">
      <TouchableOpacity
        disabled={disabled}
        onPress={onPress}
        style={[s.btn, s[variant], disabled && s.disabled]}
        accessibilityRole="button"
        accessibilityLabel={ACTION_LABEL[action.action] ?? action.label}
        accessibilityState={{ disabled }}
      >
        <Text style={s.btnText}>
          {offline ? "Requires connection" : (action.reason && !action.available ? action.reason : (ACTION_LABEL[action.action] ?? action.label))}
        </Text>
      </TouchableOpacity>
    </View>
  );
}

const s = StyleSheet.create({
  bar:      { position:"absolute", left:0, right:0, bottom:0, padding:theme.spacing.base,
              backgroundColor:theme.colors.surface, borderTopWidth:1, borderTopColor:theme.colors.border },
  btn:      { height:48, borderRadius:theme.radius.md, alignItems:"center", justifyContent:"center" },
  primary:  { backgroundColor:theme.colors.brand },
  success:  { backgroundColor:theme.colors.success },
  danger:   { backgroundColor:theme.colors.danger },
  secondary:{ backgroundColor:theme.colors.accent },
  disabled: { opacity:0.45 },
  btnText:  { color:"#fff", fontWeight:"700", fontSize:theme.font.size.md },
});
