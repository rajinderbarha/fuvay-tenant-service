import React from "react";
import { View } from "react-native";
import { useTheme, ThemePreference } from "../../design-system/theme";
import { AppButton } from "../AppButton";

/** Not part of the Home screen itself (the approved design has no visible
 * theme toggle) -- provided as a reusable settings-surface component per
 * the requested component list, for Profile/Settings to mount later. */
export function ThemeSelector() {
  const { preference, setPreference } = useTheme();
  const options: ThemePreference[] = ["system", "light", "dark"];
  return (
    <View style={{ flexDirection: "row", gap: 8 }}>
      {options.map(opt => (
        <AppButton
          key={opt}
          label={opt.charAt(0).toUpperCase() + opt.slice(1)}
          tone={preference === opt ? "primary" : "secondary"}
          size="compact"
          onPress={() => setPreference(opt)}
          accessibilityLabel={`Use ${opt} theme`}
        />
      ))}
    </View>
  );
}
