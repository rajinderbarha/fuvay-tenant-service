import { appConfig } from "./app-config";

/** Client-side fallback used until the remote feature-config endpoint (later sprint) responds. */
export const featureDefaults = appConfig.featureModuleDefaults;
