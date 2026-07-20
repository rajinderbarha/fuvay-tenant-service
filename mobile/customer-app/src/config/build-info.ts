import { environment } from "./environment";

/** Safe-to-display build metadata (no secrets). */
export const buildInfo = {
  version: environment.buildVersion,
  buildNumber: environment.buildNumber,
  environment: environment.name,
};
