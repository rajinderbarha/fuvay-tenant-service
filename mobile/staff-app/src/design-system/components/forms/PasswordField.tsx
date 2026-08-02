import React, { useState } from "react";
import { Pressable } from "react-native";
import { TextField, TextFieldProps } from "./TextField";
import { Icon } from "../Icon";
import { useTheme } from "../../themes";

export type PasswordFieldProps = Omit<TextFieldProps, "secureTextEntry" | "trailingIcon" | "autoCapitalize">;

/**
 * Secure-entry field with a show/hide toggle. `textContentType`/
 * `autoComplete` are set to the password values so iOS/Android password
 * managers can offer to fill or save credentials.
 */
export function PasswordField(props: PasswordFieldProps) {
  const { theme } = useTheme();
  const [visible, setVisible] = useState(false);

  return (
    <TextField
      {...props}
      secureTextEntry={!visible}
      autoCapitalize="none"
      autoCorrect={false}
      textContentType="password"
      autoComplete="password"
      trailingIcon={
        <Pressable
          onPress={() => setVisible(v => !v)}
          accessibilityRole="button"
          accessibilityLabel={visible ? "Hide password" : "Show password"}
          hitSlop={8}
        >
          <Icon name={visible ? "eye-off-outline" : "eye-outline"} size="standard" color={theme.colors.textSecondary} decorative />
        </Pressable>
      }
    />
  );
}
