"use client";
import { PageShell, PageHeader } from "@serviceos/design-system";
import { EvidenceGallery } from "../../../../components/ux04/EvidenceGallery";
import { FIXTURE_MEDIA_ASSETS } from "../../../../lib/ux03/fixtures";

/** DESIGN PHASE UX-04A — operational media/evidence gallery. Read-only;
 * never renders a storage key, signed URL, bucket name, or credential. */
export default function OperationalMedia() {
  return (
    <PageShell>
      <PageHeader title="Operational Media / Evidence" description="Read-only. No storage keys, signed URLs, or credentials are ever rendered." />
      <EvidenceGallery assets={FIXTURE_MEDIA_ASSETS} />
    </PageShell>
  );
}
