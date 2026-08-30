import React, { useEffect } from "react";
import { Pressable, StatusBar, StyleSheet, View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { PublicStackParamList } from "../../navigation/routeTypes";
import { SplashScreen } from "../SplashScreen";

type Nav = NativeStackNavigationProp<PublicStackParamList, "Welcome">;

/** Branded launch transition for signed-out customers.
 *
 * Now renders the Fuvay v2 splash — the animated wordmark, rule and loading
 * track from the design canvas — rather than a full-bleed PNG. The canvas's
 * splash screen IS this moment in the app, and the live version themes
 * itself light/dark, where the bitmap could not.
 *
 * Behaviour is unchanged: it advances automatically like a splash screen,
 * while the full-screen press target lets a customer skip the short delay
 * without relying on an invisible button-shaped region. The splash's own
 * animation runs longer than the 1.8s delay, so it is unmounted mid-sequence
 * by design — its drivers are stopped on unmount.
 */
export function WelcomeScreen() {
  const navigation = useNavigation<Nav>();

  useEffect(() => {
    const timer = setTimeout(() => navigation.replace("LoginMethod"), 1800);
    return () => clearTimeout(timer);
  }, [navigation]);

  return (
    <View style={styles.screen}>
      <StatusBar hidden />
      <SplashScreen />
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Continue to Fuvay sign in"
        accessibilityHint="Skips the launch screen"
        onPress={() => navigation.replace("LoginMethod")}
        style={StyleSheet.absoluteFill}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
});
