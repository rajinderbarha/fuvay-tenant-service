import React from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { AuthStackParamList } from "./routeTypes";
import { LoginScreen } from "../screens/auth/LoginScreen";
import { OtpVerifyScreen } from "../screens/auth/OtpVerifyScreen";
import { MfaScreen } from "../screens/auth/MfaScreen";
import { ForgotPasswordScreen } from "../screens/auth/ForgotPasswordScreen";
import { ResetPasswordScreen } from "../screens/auth/ResetPasswordScreen";
import { ResetSuccessScreen } from "../screens/auth/ResetSuccessScreen";

const Stack = createNativeStackNavigator<AuthStackParamList>();

/**
 * The real authentication flow (Phase G). "Otp" itself is just the mobile-
 * number entry step of LoginScreen (segmented control), not a separate
 * screen -- OtpVerify is the code-entry screen reached after "Send code".
 */
export function AuthNavigator() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="Login" component={LoginScreen} />
      <Stack.Screen name="OtpVerify" component={OtpVerifyScreen} />
      <Stack.Screen name="Mfa" component={MfaScreen} />
      <Stack.Screen name="ForgotPassword" component={ForgotPasswordScreen} />
      <Stack.Screen name="ResetPassword" component={ResetPasswordScreen} />
      <Stack.Screen name="ResetSuccess" component={ResetSuccessScreen} />
    </Stack.Navigator>
  );
}
