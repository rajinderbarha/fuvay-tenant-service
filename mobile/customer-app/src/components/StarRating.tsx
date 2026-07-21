import React from "react";
import { Text, TouchableOpacity, View } from "react-native";
import { useTheme } from "../context/ThemeContext";

interface Props { value:number; onChange?:(v:number)=>void; size?:number; readonly?:boolean }

// UX-07 Round 4 Pass 2: migrated to useTheme() (dark-mode star colors) and
// added accessible rating semantics -- each star is a real tap target
// (min 44px hit area via hitSlop) with an accessibilityLabel stating the
// value it would set, and the whole row exposes the current rating as
// text for screen readers (not implied by fill color alone).
export function StarRating({ value, onChange, size=28, readonly=false }:Props) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection:"row", gap:4 }}
      accessible={readonly} accessibilityRole={readonly ? "text" : undefined}
      accessibilityLabel={readonly ? `Rating: ${value} out of 5 stars` : undefined}>
      {[1,2,3,4,5].map(n => (
        <TouchableOpacity key={n} disabled={readonly}
          onPress={() => onChange?.(n)} activeOpacity={0.7}
          hitSlop={{ top:8, bottom:8, left:6, right:6 }}
          accessible={!readonly} accessibilityRole={readonly ? undefined : "button"}
          accessibilityLabel={readonly ? undefined : `Rate ${n} out of 5 stars`}
          accessibilityState={readonly ? undefined : { selected: n<=value }}>
          <Text style={{ fontSize:size, color:n<=value?theme.colors.star:theme.colors.starEmpty }}>★</Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}
