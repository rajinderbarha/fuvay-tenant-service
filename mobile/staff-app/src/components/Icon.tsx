import React from "react";
import { Feather } from "@expo/vector-icons";

type FeatherName = React.ComponentProps<typeof Feather>["name"];

interface Props {
  name: FeatherName;
  size?: number;
  color: string;
}

// Thin wrapper so every icon in the app comes from one real icon set
// (Feather -- same single-weight line-icon language as the web apps'
// lucide-react) instead of ad-hoc emoji/Unicode glyphs.
export function Icon({ name, size = 20, color }: Props) {
  return <Feather name={name} size={size} color={color} />;
}
