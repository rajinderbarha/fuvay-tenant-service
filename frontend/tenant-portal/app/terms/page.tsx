import { LegalDocument, LegalDocumentUnavailable } from "../../components/legal/LegalDocument";
import { fetchLegalDocument } from "../../lib/api-legal";

export const metadata = { title: "Terms of Service — ServiceOS" };

/**
 * Served from `legal_document_versions` via /v1/public/legal, not from this
 * file. The wording used to be hardcoded here, which meant a clause change
 * needed a frontend deploy and no other app could show the same text.
 *
 * `audience: "tenant"` asks for the business-workspace Terms and falls back
 * to the shared `all` version when no tenant-specific one is published.
 */
export default async function TermsPage() {
  const doc = await fetchLegalDocument("terms_of_service", { audience: "tenant" });
  if (!doc) return <LegalDocumentUnavailable title="Terms of Service" />;

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
