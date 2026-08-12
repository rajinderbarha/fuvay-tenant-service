"use client";

import { BusinessProfileWorkspace } from "../../(onboarding)/tenant/home-services/setup/business-profile/page";

/**
 * The active workspace uses the same persisted profile form as onboarding.
 * `mode="workspace"` swaps only the shell and lifecycle copy; fields,
 * validation, media and API calls remain one implementation.
 */
export default function BusinessProfilePage() {
  return <BusinessProfileWorkspace mode="workspace"/>;
}
