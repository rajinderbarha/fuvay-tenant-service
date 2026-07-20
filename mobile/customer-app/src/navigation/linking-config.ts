import * as Linking from "expo-linking";
import type { LinkingOptions } from "@react-navigation/native";
import { environment } from "../config/environment";
import { getInitialUrlOnce } from "./deep-links/initial-url-bridge";
import type { RootStackParamList } from "./route-types";

/**
 * Deliberately does NOT use React Navigation's declarative `config.screens`
 * path-to-route mapping — that mechanism would navigate straight from a raw
 * URL string with no security filtering. Instead `getInitialURL`/`subscribe`
 * only ever hand the raw string to the app's own
 * `deep-links/deep-link-resolver.ts` pipeline (parse -> validate -> guard),
 * which decides whether/where to navigate. See docs/customer-app/deep-linking.md.
 */
export const linkingConfig: LinkingOptions<RootStackParamList> = {
  prefixes: [Linking.createURL("/"), `${environment.deepLinkScheme}://`],
  config: { screens: {} },
  async getInitialURL() {
    return getInitialUrlOnce();
  },
  subscribe(listener) {
    // Re-exposes raw URL events for React Navigation's own internal
    // bookkeeping only; actual routing for these events is handled by the
    // app-resume/foreground deep-link listener wired in AppRoot.tsx, which
    // runs them through the validated resolver before calling navigate().
    const subscription = Linking.addEventListener("url", ({ url }) => listener(url));
    return () => subscription.remove();
  },
};
