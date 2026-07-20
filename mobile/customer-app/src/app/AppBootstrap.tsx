import { useEffect, useState } from "react";
import { initI18n } from "../localization/i18n-setup";
import { preferenceStorage } from "../storage/preference-storage";
import { PREFERENCE_STORAGE_KEYS } from "../storage/storage-keys";
import type { SupportedLocale } from "../config/app-config";
import { environment } from "../config/environment";
import { logger } from "../observability/logger";

/**
 * Runs one-time startup work (locale hydration + i18next init) before the
 * real app tree renders. Kept intentionally small — no business bootstrap
 * (auth session restore, etc.) belongs here; that stays in AuthProvider.
 */
export function useAppBootstrap(): { isReady: boolean } {
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const storedLocale = await preferenceStorage.getItem<SupportedLocale>(PREFERENCE_STORAGE_KEYS.localePreference);
      initI18n(storedLocale ?? undefined);
      logger.info("app.bootstrap", { environment: environment.name });
      if (!cancelled) setIsReady(true);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return { isReady };
}
