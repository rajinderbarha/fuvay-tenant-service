import React from "react";
import { View } from "react-native";
import { useTheme } from "../../themes";

export interface ButtonGroupProps {
  children: React.ReactNode;
  direction?: "row" | "column";
}

/** Lays out a set of buttons with consistent spacing -- pure layout, no
 * business logic about which actions are allowed together. */
export function ButtonGroup({ children, direction = "row" }: ButtonGroupProps) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: direction, gap: theme.spacing.sm, flexWrap: direction === "row" ? "wrap" : "nowrap" }}>
      {children}
    </View>
  );
}
