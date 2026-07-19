"use client";
import { PageShell, PageHeader, Section, Card, DataTable, EmptyState, ErrorState, PermissionDeniedState, Skeleton } from "@serviceos/design-system";

export default function StatesGalleryShowcase() {
  return (
    <PageShell>
      <PageHeader title="States Gallery" description="Loading / empty / error / read-only / restricted / long-text — light & dark inherit from ThemeProvider." />
      <Section title="Loading"><DataTable columns={[{ key: "a", header: "A" }]} rows={[]} rowKey={() => "x"} loading /></Section>
      <Section title="Empty"><EmptyState title="No tenants match your filters" description="Try broadening your search or clearing filters." /></Section>
      <Section title="Error"><ErrorState title="Couldn't load data" description="Simulated network failure for design review." /></Section>
      <Section title="Restricted / Permission Denied"><PermissionDeniedState title="You don't have access to this section" description="Contact a super_admin to request admin_finance access. Nav visibility is not itself an authorization boundary." /></Section>
      <Section title="Long / translated text">
        <Card>
          <p style={{ maxWidth: "100%", overflowWrap: "anywhere" }}>
            Ausführliche mehrsprachige Bezeichnung für einen Navigationseintrag, die deutlich länger ist als das englische Original und den Umbruch testen soll / これは非常に長いラベルのテストです。
          </p>
        </Card>
      </Section>
      <Section title="Skeleton"><Skeleton height="2.5rem" /></Section>
    </PageShell>
  );
}
