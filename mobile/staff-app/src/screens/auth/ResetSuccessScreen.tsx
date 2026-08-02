import React from "react";
import { View } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTheme } from "../../design-system/themes";
import { Screen } from "../../design-system/components/foundation/Screen";
import { Card, Stack } from "../../design-system/components/foundation/Layout";
import { AppText } from "../../design-system/components/typography/AppText";
import { Heading } from "../../design-system/components/typography/Heading";
import { PrimaryButton } from "../../design-system/components/actions/Buttons";
import { Icon } from "../../design-system/components/Icon";
import { AuthStackParamList } from "../../navigation/routeTypes";

type Props = NativeStackScreenProps<AuthStackParamList, "ResetSuccess">;

/**
 * Password-reset confirmation (Phase G spec section 7). Never
 * auto-signs-in -- the backend explicitly requires a fresh login after a
 * reset (every prior session, including any that triggered the reset
 * request, is revoked server-side).
 */
export function ResetSuccessScreen({ navigation }: Props) {
  const { theme } = useTheme();
  return (
    <Screen style={{ padding: theme.spacing.lg, justifyContent: "center" }}>
      <Card>
        <Stack gap="base">
          <View style={{ alignItems: "center" }}>
            <Icon name="checkmark-circle" size="feature" color={theme.colors.statusSuccess} decorative />
          </View>
          <Heading level="medium" align="center">Password reset</Heading>
          <AppText color="secondary" align="center">
            Your password has been changed and all previous sessions have been signed out. Sign in with your new password.
          </AppText>
          <PrimaryButton label="Back to Login" onPress={() => navigation.reset({ index: 0, routes: [{ name: "Login" }] })} fullWidth />
        </Stack>
      </Card>
    </Screen>
  );
}
