import React from "react";
import { StyleSheet, View, type ViewStyle } from "react-native";
import { theme } from "../styles/theme";

export function Card({ children, style, padding=theme.spacing.base }:{ children:React.ReactNode; style?:ViewStyle; padding?:number }) {
  return <View style={[{backgroundColor:theme.colors.surface,borderRadius:theme.radius.lg,
    padding,...theme.shadow.sm},style]}>{children}</View>;
}
