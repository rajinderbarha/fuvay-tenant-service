import React from "react";
import { AppText, AppTextProps } from "./AppText";

export interface NumericTextProps extends Omit<AppTextProps, "variant"> {
  size?: "large" | "medium";
}

/** NumericText -- tabular-numeral text for money, time and job numbers so
 * columns of numbers align. Never use a decorative font for operational data. */
export function NumericText({ size = "medium", ...rest }: NumericTextProps) {
  return <AppText variant={size === "large" ? "numericLarge" : "numericMedium"} {...rest} />;
}
