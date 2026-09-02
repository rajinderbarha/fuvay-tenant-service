"use client";

import { ArrowRight, Images } from "lucide-react";
import { PageHeader } from "@serviceos/design-system";
import { Btn, Card } from "@/components/shared/ui";

/** The former campaign-asset approval model and endpoints were retired.
 * Keep the old bookmark useful without issuing requests to removed APIs. */
export default function RetiredMarketingAssetsPage() {
  return (
    <div style={{ padding: "24px 32px", maxWidth: 960, margin: "0 auto", display: "grid", gap: 20 }}>
      <PageHeader
        title="Marketing Assets"
        description="This legacy asset-approval workspace has been retired."
        eyebrow="Marketing"
      />
      <Card>
        <div style={{ padding: 28, display: "grid", gap: 14 }}>
          <Images size={28} aria-hidden />
          <div>
            <h2 style={{ fontSize: 18, marginBottom: 6 }}>Assets now belong to posts</h2>
            <p style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}>
              The old marketing-asset approval endpoints are no longer available. Create, review,
              approve, schedule, and publish content through the posts-based Marketing workspace.
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
