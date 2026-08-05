import React, { useState } from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppInput } from "../AppInput";
import { AppIconButton } from "../AppIconButton";

export interface PasswordFieldProps {
  label?: string;
  value: string;
  onChangeText: (value: string) => void;
  error?: string;
  disabled?: boolean;
  autoComplete?: "password" | "new-password" | "current-password";
  placeholder?: string;
}

/** Secure text entry with an accessible show/hide toggle (spec section
 * 11/22) -- `secureTextEntry` is the only thing masking the value;
 * nothing here ever logs or persists it (see utils/redact.ts, which
 * treats any `password`-named field as sensitive by pattern match). */
export function PasswordField({ label = "Password", value, onChangeText, error, disabled, autoComplete = "current-password", placeholder }: PasswordFieldProps) {
  const { theme } = useTheme();
  const [visible, setVisible] = useState(false);

  return (
    <View>
      <View style={{ position: "relative", justifyContent: "center" }}>
        <AppInput
          label={label}
          value={value}
          onChangeText={onChangeText}
          secureTextEntry={!visible}
          textContentType={autoComplete === "new-password" ? "newPassword" : "password"}
          autoComplete={autoComplete}
          autoCapitalize="none"
          autoCorrect={false}
          editable={!disabled}
          error={error}
          placeholder={placeholder}
          style={{ paddingRight: theme.spacing.xxxl }}
          accessibilityLabel={label}
        />
        <View style={{ position: "absolute", right: theme.spacing.xs, top: label ? theme.spacing.xl : 0 }}>
          <AppIconButton
            name={visible ? "eye-off-outline" : "eye-outline"}
            onPress={() => setVisible(v => !v)}
            accessibilityLabel={visible ? "Hide password" : "Show password"}
          />
        </View>
      </View>
    </View>
  );
}
