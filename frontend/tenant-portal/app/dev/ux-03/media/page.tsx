import { PageShell, PageHeader, Card } from "@serviceos/design-system";
import { FIXTURE_MEDIA_ASSETS } from "../../../../lib/ux03/fixtures";

export default function Media() {
  return (
    <PageShell>
      <PageHeader title="Media" description="Upload/replace/preview presentation only — storage keys, signed URLs, and credentials are never exposed. See N01 media-integrity backlog (known-limitations.md)." />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px,1fr))", gap: "1rem" }}>
        {FIXTURE_MEDIA_ASSETS.map((m) => (
          <Card key={m.id} title={m.label}>
            <p style={{ fontSize: "0.8rem" }}>{m.kind} · {m.sizeLabel}</p>
            <p style={{ fontSize: "0.7rem", color: "var(--text-secondary)" }}>preview token: {m.previewToken} (not a signed URL)</p>
          </Card>
        ))}
      </div>
    </PageShell>
  );
}
