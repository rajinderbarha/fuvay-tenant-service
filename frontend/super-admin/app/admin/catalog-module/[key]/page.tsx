"use client";
import { useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Construction } from "lucide-react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Btn, SectionHeader, Skeleton } from "../../../../components/shared/ui";
import { verticalCatalogApi, type CatalogModuleItem } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";

export default function CatalogModulePlaceholderPage() {
  const params = useParams<{ key: string }>();
  const router = useRouter();
  const moduleKey = params?.key ?? "";

  const modules = useApi(useCallback(() => verticalCatalogApi.listModules(), []));
  const mod: CatalogModuleItem | undefined =
    (modules.data?.items ?? []).find(m => m.key === moduleKey);

  return (
    <AdminLayout activeNav={`catalog-module-${moduleKey}`}>
      <SectionHeader
        title={mod?.label ?? moduleKey}
        subtitle="This vertical's catalog module."
        actions={<Btn variant="ghost" size="sm" icon={<ArrowLeft size={14} />} onClick={() => router.back()}>Back</Btn>}
      />
      <div style={{ padding: "0 28px 32px" }}>
        {modules.loading ? <Skeleton height={200} /> : (
          <Card padding={40}>
            <div style={{ textAlign: "center", color: "var(--text-tertiary)" }}>
              <Construction size={32} style={{ marginBottom: 12, opacity: 0.6 }} />
              <p style={{ fontSize: 15, fontWeight: 600, margin: "0 0 6px", color: "var(--text-primary)" }}>
                {mod?.label ?? moduleKey}
              </p>
              <p style={{ fontSize: 13, margin: 0 }}>
                Dedicated admin UI for this module is coming soon. This module is enabled for its
                vertical and appears in the sidebar, but its full management screen has not been
                built yet.
              </p>
            </div>
          </Card>
        )}
      </div>
    </AdminLayout>
  );
}
