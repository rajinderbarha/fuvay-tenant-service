import {
  Barlow_400Regular,
  Barlow_500Medium,
  Barlow_600SemiBold,
  Barlow_700Bold,
  useFonts,
} from "@expo-google-fonts/barlow";
import {
  JetBrainsMono_400Regular,
  JetBrainsMono_500Medium,
} from "@expo-google-fonts/jetbrains-mono";

/**
 * Loads the Fuvay v2 typefaces.
 *
 * Only the four Barlow weights the v2 type scale actually uses are loaded
 * (400/500/600/700) plus two JetBrains Mono weights for metadata labels —
 * the packages ship 18 Barlow faces each with an italic, and bundling all of
 * them would cost several hundred KB of TTF for weights no screen asks for.
 *
 * Returns `true` once the faces are registered. Callers should NOT block the
 * whole app on this: React Native falls back to the system font for an
 * unregistered family, so rendering before it resolves shows correctly-laid-
 * out text in the wrong face for a frame, which is far better than a blank
 * screen. Gate only a splash screen on it, if anything.
 */
export function useFuvayFonts(): boolean {
  const [loaded] = useFonts({
    Barlow_400Regular,
    Barlow_500Medium,
    Barlow_600SemiBold,
    Barlow_700Bold,
    JetBrainsMono_400Regular,
    JetBrainsMono_500Medium,
  });
  return loaded;
}
