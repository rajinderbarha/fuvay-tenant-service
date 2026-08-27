import React from "react";
import { useNavigation } from "@react-navigation/native";
import { ProfileRow } from "./ProfileRow";
import { IconProps } from "../Icon";
import { useLegalDocumentIndexQuery } from "../../api/legalDocuments/useLegalDocumentQueries";

export interface LegalLinksProps {
  appVersion: string;
}

/**
 * Privacy / Terms rows in the profile's "Privacy & legal" section.
 *
 * These used to take `privacyPolicyUrl` / `termsOfServiceUrl` and open them
 * externally, subject to an `*.fuvay.com` allowlist. ProfileScreen passed
 * `null` for both and the component omits unconfigured rows, so in practice
 * neither row had ever rendered — the section showed only "About Fuvay".
 *
 * Rows are now driven by /v1/public/legal, which lists exactly the documents
 * that have a published version. A document type with nothing published is
 * still omitted, so a row can never lead to an empty screen — but now that is
 * a real check against the store, not a hardcoded `null`.
 */

const ICON_BY_DOC_TYPE: Record<string, IconProps["name"]> = {
  privacy_policy: "shield-checkmark-outline",
  terms_of_service: "document-text-outline",
  refund_policy: "cash-outline",
  cookie_policy: "settings-outline",
  acceptable_use: "alert-circle-outline",
};

export function LegalLinks({ appVersion }: LegalLinksProps) {
  const navigation = useNavigation<{
    navigate: (screen: string, params: { docType: string; title: string }) => void;
  }>();
  const index = useLegalDocumentIndexQuery();

  const documents = index.data?.documents ?? [];

  return (
    <>
      {documents.map(doc => (
        <ProfileRow
          key={doc.doc_type}
          icon={ICON_BY_DOC_TYPE[doc.doc_type] ?? "document-outline"}
          label={doc.title}
          onPress={() => navigation.navigate("LegalDocument", {
            docType: doc.doc_type,
            title: doc.title,
          })}
        />
      ))}
      <ProfileRow
        icon="information-circle-outline"
        label="About Fuvay"
        subtitle={`Version ${appVersion}`}
        bordered={false}
      />
    </>
  );
}
