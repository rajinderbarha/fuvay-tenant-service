import React from "react";
import { Pressable } from "react-native";
import { TextField, TextFieldProps } from "./TextField";
import { Icon } from "../Icon";
import { useTheme } from "../../themes";

export type SearchFieldProps = Omit<TextFieldProps, "leadingIcon" | "trailingIcon"> & {
  onClear?: () => void;
};

export function SearchField({ value, onClear, ...rest }: SearchFieldProps) {
  const { theme } = useTheme();
  return (
    <TextField
      value={value}
      returnKeyType="search"
      leadingIcon={<Icon name="search-outline" size="standard" color={theme.colors.textTertiary} decorative />}
      trailingIcon={
        value && onClear ? (
          <Pressable onPress={onClear} accessibilityRole="button" accessibilityLabel="Clear search" hitSlop={8}>
            <Icon name="close-circle" size="standard" color={theme.colors.textTertiary} decorative />
          </Pressable>
        ) : undefined
      }
      {...rest}
    />
  );
}
