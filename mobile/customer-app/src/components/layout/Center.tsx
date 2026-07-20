import React from "react";
import { View, type ViewStyle } from "react-native";

export function Center({ children, style }: { children: React.ReactNode; style?: ViewStyle }) {
  return <View style={[{ alignItems: "center", justifyContent: "center" }, style]}>{children}</View>;
}
