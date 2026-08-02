import React from "react";
import { ScrollView } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme, ThemePreference } from "../../design-system/themes";
import { SafeAreaScreen } from "../../design-system/components/foundation/SafeAreaScreen";
import { Card, Section } from "../../design-system/components/foundation/Layout";
import { Radio } from "../../design-system/components/forms/Radio";
import { ScreenHeader } from "./components/ScreenHeader";
import { ProfileStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<ProfileStackParamList, "Appearance">;

const OPTIONS: { key: ThemePreference; label: string }[] = [
  { key: "system", label: "System" },
  { key: "light", label: "Light" },
  { key: "dark", label: "Dark" },
];

/**
 * Appearance (Phase R spec section 12). Pure UI wiring onto the existing
 * ThemeProvider -- no new persistence. Deliberately no language row/selector
 * per explicit instruction: ServiceOS app interfaces remain single-language.
 */
export function AppearanceScreen({ navigation }: Props) {
  const { theme, preference, setPreference } = useTheme();
  return (
    <SafeAreaScreen edges={["top", "left", "right"]}>
      <ScreenHeader title="Appearance" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg }}>
        <Section>
          <Card padding="base">
            {OPTIONS.map(opt => (
              <Radio key={opt.key} label={opt.label} selected={preference === opt.key} onSelect={() => setPreference(opt.key)} />
            ))}
          </Card>
        </Section>
      </ScrollView>
    </SafeAreaScreen>
  );
}
