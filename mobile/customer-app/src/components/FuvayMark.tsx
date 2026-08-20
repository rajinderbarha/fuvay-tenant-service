import React from "react";
import { Image, View } from "react-native";

/** Official Fuvay artwork shared by auth/bootstrap/exceptional-state screens. */
export function FuvayMark() {
  return (
    <View accessibilityRole="image" accessibilityLabel="Fuvay" style={{ width: 178, height: 48, overflow: "hidden" }}>
      <Image source={require("../../assets/fuvay-logo-native.png")} resizeMode="contain" style={{ width: 178, height: 48 }} />
    </View>
  );
}
