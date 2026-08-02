import React from "react";
import { AppText, AppTextProps } from "./AppText";

export interface HeadingProps extends Omit<AppTextProps, "variant"> {
  level?: "display" | "large" | "medium" | "small";
}

const VARIANT_MAP = {
  display: "displayLarge",
  large: "headingLarge",
  medium: "headingMedium",
  small: "headingSmall",
} as const;

/** Heading -- always exposes the "header" accessibility role so screen
 * readers can navigate by heading, matching web `<h1>`-style semantics. */
export function Heading({ level = "medium", ...rest }: HeadingProps) {
  return (
    <AppText
      variant={VARIANT_MAP[level]}
      accessibilityRole="header"
      {...rest}
    />
  );
}
