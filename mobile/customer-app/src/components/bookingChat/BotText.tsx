import React, { useMemo } from "react";
import { StyleSheet, Text, TextProps, TextStyle } from "react-native";

import { fuvayFontFamily } from "../../design-system/tokens/fonts";

/**
 * Text primitive for the AI booking assistant — Fuvay v2.
 *
 * ── Why this exists ───────────────────────────────────────────────────────
 * The rest of the app reaches the v2 type scale through `AppText`, which
 * applies `theme.typography[variant]`. The assistant flow never did: its 15
 * files styled text with ~140 inline `fontSize` values on React Native's raw
 * `Text` and imported `AppText` in none of them. Since a custom TTF is only
 * selected by FAMILY NAME (see tokens/fonts.ts), those call sites silently
 * rendered in the SYSTEM font while Home, Splash and Login rendered in
 * Barlow — the single most visible reason the four canvas screens did not
 * look like one app.
 *
 * Rewriting ~140 sites onto `AppText` variants would mean re-deciding every
 * size in a flow whose spacing is tuned to them, so this keeps the existing
 * sizes and supplies the one thing that was missing: the family.
 *
 * ── The mapping rule ──────────────────────────────────────────────────────
 * Identical to the type scale's: derive the family from the declared
 * `fontWeight`, and KEEP that `fontWeight` in the style. It is not
 * redundant — it is the only weight signal left if the TTFs have not
 * registered yet (first frame, or unit tests, which never load fonts), where
 * RN falls back to the system font and would otherwise render every heading
 * at regular weight.
 *
 * An explicit `fontFamily` on the caller's style always wins untouched, so
 * the mono metadata labels keep JetBrains Mono.
 */

function familyForWeight(weight: TextStyle["fontWeight"]): string {
  switch (String(weight ?? "400")) {
    case "500":
      return fuvayFontFamily.medium;
    case "600":
      return fuvayFontFamily.semibold;
    case "700":
    case "800":
    case "900":
    case "bold":
      return fuvayFontFamily.bold;
    default:
      return fuvayFontFamily.regular;
  }
}

/** Drop-in replacement for `Text` inside the assistant flow. Font scaling is
 *  left ENABLED, matching AppText — never globally disable OS font scaling. */
export function BotText({ style, ...rest }: TextProps) {
  const resolved = useMemo(() => {
    const flat = StyleSheet.flatten(style) as TextStyle | undefined;
    if (flat?.fontFamily) return flat;
    return { ...(flat ?? {}), fontFamily: familyForWeight(flat?.fontWeight) };
  }, [style]);

  return <Text style={resolved} {...rest} />;
}
