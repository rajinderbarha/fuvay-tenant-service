import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { Icon, IconProps } from "../Icon";
import { BottomSheet } from "./BottomSheet";

export interface ActionSheetOption {
  key: string;
  label: string;
  icon?: IconProps["name"];
  destructive?: boolean;
  disabled?: boolean;
}

export interface ActionSheetProps {
  visible: boolean;
  title?: string;
  options: ActionSheetOption[];
  onSelect: (key: string) => void;
  onClose: () => void;
}

export function ActionSheet({ visible, title, options, onSelect, onClose }: ActionSheetProps) {
  const { theme } = useTheme();
  return (
    <BottomSheet visible={visible} onClose={onClose}>
      {title ? <AppText variant="label" color="tertiary" style={{ marginBottom: theme.spacing.sm }}>{title}</AppText> : null}
      {options.map(opt => (
        <Pressable
          key={opt.key}
          onPress={() => { if (!opt.disabled) { onSelect(opt.key); onClose(); } }}
          disabled={opt.disabled}
          accessibilityRole="menuitem"
          accessibilityLabel={opt.label}
          accessibilityState={{ disabled: opt.disabled }}
          style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, paddingVertical: theme.spacing.md, opacity: opt.disabled ? theme.opacity.disabled : 1 }}
        >
          {opt.icon ? <Icon name={opt.icon} size="standard" color={opt.destructive ? theme.colors.statusDanger : theme.colors.textPrimary} decorative /> : null}
          <AppText variant="body" color={opt.destructive ? "danger" : "primary"}>{opt.label}</AppText>
        </Pressable>
      ))}
    </BottomSheet>
  );
}
