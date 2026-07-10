import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { theme } from "../styles/theme";

interface Props { value:number; onChange?:(v:number)=>void; size?:number; readonly?:boolean }

export function StarRating({ value, onChange, size=28, readonly=false }:Props) {
  return (
    <View style={{ flexDirection:"row", gap:4 }}>
      {[1,2,3,4,5].map(n => (
        <TouchableOpacity key={n} disabled={readonly}
          onPress={() => onChange?.(n)} activeOpacity={0.7}>
          <Text style={{ fontSize:size, color:n<=value?theme.colors.star:theme.colors.starEmpty }}>★</Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}
