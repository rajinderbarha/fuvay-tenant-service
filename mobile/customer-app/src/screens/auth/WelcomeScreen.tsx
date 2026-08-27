import React, { useEffect } from "react";
import { ImageBackground, Pressable, StatusBar, StyleSheet, View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { PublicStackParamList } from "../../navigation/routeTypes";

type Nav = NativeStackNavigationProp<PublicStackParamList, "Welcome">;

/** Branded launch transition for signed-out customers.
 *
 * The artwork intentionally has no button. It advances automatically like a
 * splash screen, while the full-screen press target lets a customer skip the
 * short delay without relying on an invisible button-shaped region.
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
      <ImageBackground
        source={require("../../../assets/splash-screen.png")}
        resizeMode="cover"
        style={styles.artwork}
        accessibilityIgnoresInvertColors
      >
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Continue to Fuvay sign in"
          accessibilityHint="Skips the launch screen"
          onPress={() => navigation.replace("LoginMethod")}
          style={StyleSheet.absoluteFill}
        />
      </ImageBackground>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#0A5BFF" },
  artwork: { flex: 1, width: "100%" },
});
