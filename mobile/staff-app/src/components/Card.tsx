import React from "react";
import { StyleSheet, View, type ViewStyle } from "react-native";
import { theme } from "../styles/theme";

interface Props { children:React.ReactNode; style?:ViewStyle; padding?:number }

export function Card({ children, style, padding=theme.spacing.base }: Props) {
  return <View style={[s.card, { padding }, style]}>{children}</View>;
}

const s = StyleSheet.create({
  card: {
    backgroundColor:theme.colors.surface,
    borderRadius:theme.radius.lg,
    ...theme.shadow.sm,
  },
});
