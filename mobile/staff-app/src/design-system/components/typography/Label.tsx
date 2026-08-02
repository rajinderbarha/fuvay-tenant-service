import React from "react";
import { AppText, AppTextProps } from "./AppText";

export interface LabelProps extends Omit<AppTextProps, "variant"> {
  strong?: boolean;
}

/** Label -- small uppercase-style metadata text (field labels, section eyebrows). */
export function Label({ strong = false, ...rest }: LabelProps) {
  return <AppText variant={strong ? "labelStrong" : "label"} color="secondary" {...rest} />;
}

/** Caption -- smallest readable text (timestamps, footnotes). Never smaller
 * than this -- section 10 requires a minimum readable caption size. */
export function Caption(rest: Omit<AppTextProps, "variant">) {
  return <AppText variant="caption" color="tertiary" {...rest} />;
}
