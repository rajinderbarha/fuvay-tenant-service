import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import * as Localization from "expo-localization";
import { SUPPORTED_LOCALES, type SupportedLocale } from "../config/app-config";
import { setRequestLocale } from "../api/request-context";

import enCommon from "./locales/en/common.json";
import enShowcase from "./locales/en/showcase.json";
import enStartup from "./locales/en/startup.json";
import enDiscovery from "./locales/en/discovery.json";
import hiCommon from "./locales/hi/common.json";
import hiShowcase from "./locales/hi/showcase.json";
import hiStartup from "./locales/hi/startup.json";
import hiDiscovery from "./locales/hi/discovery.json";
import paCommon from "./locales/pa/common.json";
import paShowcase from "./locales/pa/showcase.json";
import paStartup from "./locales/pa/startup.json";
import paDiscovery from "./locales/pa/discovery.json";

const resources = {
  en: { common: enCommon, showcase: enShowcase, startup: enStartup, discovery: enDiscovery },
  hi: { common: hiCommon, showcase: hiShowcase, startup: hiStartup, discovery: hiDiscovery },
  pa: { common: paCommon, showcase: paShowcase, startup: paStartup, discovery: paDiscovery },
};

function detectSystemLocale(): SupportedLocale {
  const tag = Localization.getLocales()[0]?.languageCode ?? "en";
  const supported = SUPPORTED_LOCALES.find((locale) => locale.code === tag);
  return supported?.code ?? "en";
}

export function initI18n(persistedLocale?: SupportedLocale): typeof i18n {
  if (!i18n.isInitialized) {
    const initialLocale = persistedLocale ?? detectSystemLocale();
    void i18n.use(initReactI18next).init({
      resources,
      lng: initialLocale,
      fallbackLng: "en",
      ns: ["common", "showcase", "startup", "discovery"],
      defaultNS: "common",
      interpolation: { escapeValue: false },
      // RTL-readiness: current locales are all LTR, but the interpolation
      // and formatting layer here does not assume LTR.
      compatibilityJSON: "v4",
    });
    // The API client's Accept-Language header (api/request-context.ts,
    // CUSTOMER-L5-00) must always match the app's actual resolved locale —
    // previously nothing ever called setRequestLocale, so every request
    // silently claimed "en" regardless of the customer's real language.
    setRequestLocale(initialLocale);
    i18n.on("languageChanged", (lng) => setRequestLocale(lng));
  }
  return i18n;
}

export { i18n };
export { detectSystemLocale };
