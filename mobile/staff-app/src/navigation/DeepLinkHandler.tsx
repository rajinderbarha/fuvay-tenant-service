import { useEffect, useRef } from "react";
import * as Linking from "expo-linking";
import { parseDeepLink, setPendingDeepLink, consumePendingDeepLink, ParsedDeepLink } from "./deepLinking";
import { resolveAuthorizedRoute } from "./guards/resolveAuthorizedRoute";
import { JobRouteAdapter } from "./guards/validateJobRoute";
import { navigationRef } from "./navigationRef";
import { useSession } from "./session/SessionProvider";
import Constants from "expo-constants";

const CURRENT_APP_VERSION = Constants.expoConfig?.version ?? "0.0.0";

/** Phase E has no real job API -- job deep links fail closed to
 * ENTITY_NOT_FOUND rather than being treated as authorized. Phase F swaps
 * this for a TanStack Query-backed adapter without touching this file. */
const notYetImplementedJobAdapter: JobRouteAdapter = {
  async fetchJobSummary() { return null; },
};

function openParsedLink(link: ParsedDeepLink) {
  if (!navigationRef.isReady()) return;
  const { routeKey, jobId } = link;
  if (jobId) {
    navigationRef.navigate("JobExecutionStack", { screen: "JobDetail", params: { jobId } });
  } else {
    const tabScreen: Record<string, string> = { HOME: "Home", JOBS: "Jobs", SCHEDULE: "Schedule", NOTIFICATIONS: "Notifications", PROFILE: "Profile" };
    const name = tabScreen[routeKey];
    if (name) navigationRef.navigate("AppTabs", { screen: name } as never);
  }
}

/**
 * Mounted once, above RootNavigator. Handles cold start + foreground deep
 * links (spec section 8): unknown links fail closed silently (no
 * navigation), protected links wait for bootstrap, unauthenticated
 * protected links are stashed as a single pending destination and
 * revalidated (never blindly replayed) once authenticated_ready.
 */
export function DeepLinkHandler(): null {
  const { bootstrapState, accessContext } = useSession();
  const consumedInitialUrl = useRef(false);

  useEffect(() => {
    async function handleUrl(url: string) {
      const link = parseDeepLink(url);
      if (!link) return; // fails closed -- unknown/malformed/malicious URL

      if (bootstrapState !== "authenticated_ready") {
        setPendingDeepLink(link);
        return;
      }

      const result = await resolveAuthorizedRoute({
        routeKey: link.routeKey,
        jobId: link.jobId,
        accessContext,
        currentAppVersion: CURRENT_APP_VERSION,
        jobAdapter: notYetImplementedJobAdapter,
      });
      if (result.allowed) openParsedLink(link);
      // Denials are silent from the deep link's perspective -- the app
      // simply stays on its current authorized screen; no customer data or
      // internal reason is ever surfaced from a bare link tap.
    }

    if (!consumedInitialUrl.current) {
      consumedInitialUrl.current = true;
      Linking.getInitialURL().then(url => { if (url) handleUrl(url); });
    }

    const sub = Linking.addEventListener("url", ({ url }) => handleUrl(url));
    return () => sub.remove();
  }, [bootstrapState, accessContext]);

  useEffect(() => {
    if (bootstrapState !== "authenticated_ready") return;
    const pending = consumePendingDeepLink();
    if (!pending) return;
    resolveAuthorizedRoute({
      routeKey: pending.routeKey,
      jobId: pending.jobId,
      accessContext,
      currentAppVersion: CURRENT_APP_VERSION,
      jobAdapter: notYetImplementedJobAdapter,
    }).then(result => {
      if (result.allowed) openParsedLink(pending);
    });
  }, [bootstrapState, accessContext]);

  return null;
}
