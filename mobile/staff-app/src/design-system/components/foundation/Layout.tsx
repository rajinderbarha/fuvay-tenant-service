import React from "react";
import { View, ViewProps } from "react-native";
import { useTheme } from "../../themes";
import { SpacingToken } from "../../tokens/spacing";

/** Surface -- a themed background block with no padding/elevation opinion. */
export function Surface({ style, children, ...rest }: ViewProps) {
  const { theme } = useTheme();
  return <View style={[{ backgroundColor: theme.colors.surfaceDefault }, style]} {...rest}>{children}</View>;
}

export interface CardProps extends ViewProps {
  padding?: SpacingToken;
  elevation?: "sm" | "md" | "lg" | "none";
}

/** Card -- raised surface, large radius, subtle shadow. Dark mode leans on
 * the border for hierarchy since shadow reads poorly on dark backgrounds. */
export function Card({ style, children, padding = "base", elevation = "sm", ...rest }: CardProps) {
  const { theme } = useTheme();
  return (
    <View
      style={[
        {
          backgroundColor: theme.colors.surfaceRaised,
          borderRadius: theme.radiusUsage.card,
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          padding: theme.spacing[padding],
        },
        elevation !== "none" ? theme.shadow[elevation] : null,
        style,
      ]}
      {...rest}
    >
      {children}
    </View>
  );
}

export interface SectionProps extends ViewProps {
  spacing?: SpacingToken;
}

/** Section -- vertical block with consistent bottom spacing between page sections. */
export function Section({ style, children, spacing = "xl", ...rest }: SectionProps) {
  const { theme } = useTheme();
  return <View style={[{ marginBottom: theme.spacing[spacing] }, style]} {...rest}>{children}</View>;
}

export interface StackProps extends ViewProps {
  gap?: SpacingToken;
}

/** Stack -- vertical flex layout with a gap. */
export function Stack({ style, children, gap = "sm", ...rest }: StackProps) {
  const { theme } = useTheme();
  return <View style={[{ flexDirection: "column", gap: theme.spacing[gap] }, style]} {...rest}>{children}</View>;
}

export interface InlineProps extends ViewProps {
  gap?: SpacingToken;
  align?: "center" | "flex-start" | "flex-end" | "stretch";
  justify?: "flex-start" | "flex-end" | "center" | "space-between" | "space-around";
  wrap?: boolean;
}

/** Inline -- horizontal flex layout with a gap. */
export function Inline({ style, children, gap = "sm", align = "center", justify = "flex-start", wrap = false, ...rest }: InlineProps) {
  const { theme } = useTheme();
  return (
    <View
      style={[
        { flexDirection: "row", gap: theme.spacing[gap], alignItems: align, justifyContent: justify, flexWrap: wrap ? "wrap" : "nowrap" },
        style,
      ]}
      {...rest}
    >
      {children}
    </View>
  );
}

export function Divider({ style }: { style?: ViewProps["style"] }) {
  const { theme } = useTheme();
  return <View style={[{ height: 1, backgroundColor: theme.colors.borderSubtle }, style]} accessibilityElementsHidden importantForAccessibility="no-hide-descendants" />;
}

export function Spacer({ size = "base" }: { size?: SpacingToken }) {
  const { theme } = useTheme();
  return <View style={{ height: theme.spacing[size], width: theme.spacing[size] }} />;
}
