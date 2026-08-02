import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";

export interface InfoRowProps {
  label: string;
  value: string;
}

export function InfoRow({ label, value }: InfoRowProps) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", justifyContent: "space-between", paddingVertical: theme.spacing.xs, gap: theme.spacing.sm }}>
      <AppText variant="bodySmall" color="tertiary">{label}</AppText>
      <AppText variant="bodySmall" style={{ flexShrink: 1, textAlign: "right" }}>{value}</AppText>
    </View>
  );
}

export function KeyValueList({ items }: { items: InfoRowProps[] }) {
  const { theme } = useTheme();
  return (
    <View style={{ gap: theme.spacing.xxs }}>
      {items.map((item, i) => <InfoRow key={`${item.label}-${i}`} {...item} />)}
    </View>
  );
}

export function SectionHeader({ title, action }: { title: string; action?: React.ReactNode }) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: theme.spacing.sm }}>
      <AppText variant="title">{title}</AppText>
      {action}
    </View>
  );
}

export function ListRow({ title, subtitle, trailing, onPress }: { title: string; subtitle?: string; trailing?: React.ReactNode; onPress?: () => void }) {
  const { theme } = useTheme();
  const content = (
    <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: theme.spacing.sm, gap: theme.spacing.sm }}>
      <View style={{ flex: 1 }}>
        <AppText variant="body">{title}</AppText>
        {subtitle ? <AppText variant="caption" color="tertiary">{subtitle}</AppText> : null}
      </View>
      {trailing}
    </View>
  );
  if (!onPress) return content;
  return <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={title}>{content}</Pressable>;
}
