"use client";

import { ArrowRight, LayoutTemplate } from "lucide-react";
import { PageHeader } from "@serviceos/design-system";
import { Btn, Card } from "@/components/shared/ui";

/** The former channel/title/body template shape has no backing model. The
 * canonical marketing engine uses post content templates instead. */
export default function RetiredMarketingTemplatesPage() {
  return (
    <div style={{ padding: "24px 32px", maxWidth: 960, margin: "0 auto", display: "grid", gap: 20 }}>
      <PageHeader
        title="Marketing Templates"
        description="This legacy template workspace has been retired."
        eyebrow="Marketing"
      />
      <Card>
        <div style={{ padding: 28, display: "grid", gap: 14 }}>
          <LayoutTemplate size={28} aria-hidden />
          <div>
            <h2 style={{ fontSize: 18, marginBottom: 6 }}>Use content templates</h2>
            <p style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}>
              Channel placeholder templates are no longer a supported model. Manage the real
              prompt, caption, hashtag, and call-to-action templates in the Marketing workspace.
            </p>
          </div>
          <div>
            <Btn onClick={() => { window.location.href = "/admin/marketing"; }}>
              Open Marketing Workspace <ArrowRight size={14} />
            </Btn>
          </div>
        </div>
      </Card>
    </div>
  );
}
