import React from "react";
import { Linking, Alert } from "react-native";
import { ProfileRow } from "./ProfileRow";

export interface LegalLinksProps {
  privacyPolicyUrl: string | null;
  termsOfServiceUrl: string | null;
  appVersion: string;
}

const ALLOWED_HOSTS_SUFFIX = ".fuvay.com";

/** Only ever opens a configured HTTPS URL on an allowed host -- never an
 * arbitrary string from anywhere else (spec section 11). Rows for
 * unconfigured URLs are omitted entirely, not shown disabled. */
function isAllowedLegalUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" && parsed.hostname.endsWith(ALLOWED_HOSTS_SUFFIX);
  } catch {
    return false;
  }
}

async function openExternal(url: string) {
  if (!isAllowedLegalUrl(url)) return;
  const supported = await Linking.canOpenURL(url);
  if (supported) {
    await Linking.openURL(url);
  } else {
    Alert.alert("Couldn't open link", "Please try again later.");
  }
}

export function LegalLinks({ privacyPolicyUrl, termsOfServiceUrl, appVersion }: LegalLinksProps) {
  return (
    <>
      {privacyPolicyUrl ? (
        <ProfileRow icon="shield-checkmark-outline" label="Privacy policy" external onPress={() => openExternal(privacyPolicyUrl)} />
      ) : null}
      {termsOfServiceUrl ? (
        <ProfileRow icon="document-text-outline" label="Terms of service" external onPress={() => openExternal(termsOfServiceUrl)} />
      ) : null}
      <ProfileRow icon="information-circle-outline" label="About Fuvay" subtitle={`Version ${appVersion}`} bordered={false} />
    </>
  );
}
