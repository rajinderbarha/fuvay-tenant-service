import React from "react";
import { View, type ViewStyle } from "react-native";
import { useTheme } from "../context/ThemeContext";

// UX-07 Round 4 Pass 2: migrated off the static `theme` import onto
// `useTheme()` so every screen using <Card/> (the majority of the app)
// automatically renders correctly in dark mode without per-screen changes.
export function Card({ children, style, padding }:{ children:React.ReactNode; style?:ViewStyle; padding?:number }) {
  const { theme } = useTheme();
  return <View style={[{backgroundColor:theme.colors.surfaceCard,borderRadius:theme.radius.lg,
    padding:padding ?? theme.spacing.base,...theme.shadow.sm},style]}>{children}</View>;
}
