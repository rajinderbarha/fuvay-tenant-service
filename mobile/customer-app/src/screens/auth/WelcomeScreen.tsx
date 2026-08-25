import React from "react";
import { ImageBackground, Pressable, StatusBar, StyleSheet, View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { PublicStackParamList } from "../../navigation/routeTypes";

type Nav = NativeStackNavigationProp<PublicStackParamList, "Welcome">;

/** Approved Fuvay artwork with a real native action over its visual CTA. */
export function WelcomeScreen() {
  const navigation = useNavigation<Nav>();

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
          accessibilityLabel="Get started with Fuvay"
          accessibilityHint="Opens customer sign in and registration"
          onPress={() => navigation.replace("LoginMethod")}
          style={({ pressed }) => [styles.getStartedTarget, pressed && styles.pressed]}
        />
      </ImageBackground>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#0A5BFF" },
  artwork: { flex: 1, width: "100%", justifyContent: "flex-end", alignItems: "center" },
  getStartedTarget: { width: "58%", height: "6.8%", marginBottom: "5.4%", borderRadius: 18 },
  pressed: { backgroundColor: "rgba(10, 91, 255, 0.08)" },
});
