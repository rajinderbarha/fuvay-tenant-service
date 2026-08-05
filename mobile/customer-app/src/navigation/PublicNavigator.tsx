import React from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { PublicStackParamList } from "./routeTypes";
import { LoginMethodScreen } from "../screens/auth/LoginMethodScreen";
import { VerifyLoginOtpScreen } from "../screens/auth/VerifyLoginOtpScreen";
import { PasswordLoginScreen } from "../screens/auth/PasswordLoginScreen";
import { MfaChallengeScreen } from "../screens/auth/MfaChallengeScreen";
import { RecoveryCodeChallengeScreen } from "../screens/auth/RecoveryCodeChallengeScreen";
import { ForgotPasswordRequestScreen } from "../screens/auth/ForgotPasswordRequestScreen";
import { ResetPasswordConfirmScreen } from "../screens/auth/ResetPasswordConfirmScreen";

const Stack = createNativeStackNavigator<PublicStackParamList>();

/**
 * Owns the real typed public-route structure (Phase G, replacing the
 * Phase E placeholder). Every screen here goes through the verified
 * Phase F session manager (api/session/sessionManager.ts) -- there is no
 * second token store, no fake authentication, no direct navigation to
 * the customer shell from a submit handler (that happens globally via
 * RootNavigator reacting to session-state changes).
 */
export function PublicNavigator() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="LoginMethod" component={LoginMethodScreen} />
      <Stack.Screen name="VerifyLoginOtp" component={VerifyLoginOtpScreen} />
      <Stack.Screen name="PasswordLogin" component={PasswordLoginScreen} />
      <Stack.Screen name="MfaChallenge" component={MfaChallengeScreen} />
      <Stack.Screen name="RecoveryCodeChallenge" component={RecoveryCodeChallengeScreen} />
      <Stack.Screen name="ForgotPasswordRequest" component={ForgotPasswordRequestScreen} />
      <Stack.Screen name="ResetPasswordConfirm" component={ResetPasswordConfirmScreen} />
    </Stack.Navigator>
  );
}
