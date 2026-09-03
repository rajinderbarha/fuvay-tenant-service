import { LegalDocument, LegalDocumentUnavailable } from "../../components/legal/LegalDocument";
import { fetchLegalDocument } from "../../lib/api-legal";

export const metadata = { title: "Privacy Notice — Fuvay" };

/** See app/terms/page.tsx — same pattern, same reason. */
export default async function PrivacyPage() {
  const doc = await fetchLegalDocument("privacy_policy", { audience: "tenant" });
  if (!doc) return <LegalDocumentUnavailable title="Privacy Notice" />;

  return (
    <LegalDocument
      title={doc.title}
      intro={doc.summary}
      version={doc.version}
      updated={new Date(doc.effective_at ?? doc.published_at ?? Date.now()).toLocaleDateString("en-GB", {
        day: "numeric", month: "long", year: "numeric",
      })}
      body={doc.body}
    />
  );
}
