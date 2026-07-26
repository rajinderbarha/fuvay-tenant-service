"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  serviceSetupTemplatesApi,
  type SetupTemplateDetail,
} from "../../../../../lib/api";
import { useApi, useAction } from "../../../../../hooks/useApi";
import { Btn } from "../../../../../components/shared/ui";

const STATUS_STYLES: Record<string, { bg: string; color: string }> = {
  draft:     { bg: "var(--warning-bg)", color: "var(--warning-text)" },
  published: { bg: "var(--success-bg)", color: "var(--success-text)" },
  archived:  { bg: "var(--surface-sunken)", color: "var(--text-tertiary)" },
};

export default function TemplateDetailPage() {
  const { templateId } = useParams<{ templateId: string }>();
  const router = useRouter();

  const { data: template, loading, error, requestId, refetch } = useApi(
    useCallback(() => serviceSetupTemplatesApi.get(templateId), [templateId]),
  );

  const publishAction = useAction(useCallback(() => serviceSetupTemplatesApi.publish(templateId), [templateId]));
  const archiveAction = useAction(useCallback(() => serviceSetupTemplatesApi.archive(templateId), [templateId]));
  const cloneAction   = useAction(useCallback(() => serviceSetupTemplatesApi.clone(templateId), [templateId]));
  const deleteAction  = useAction(useCallback(() => serviceSetupTemplatesApi.delete(templateId), [templateId]));
  const validateAction = useAction(useCallback(() => serviceSetupTemplatesApi.validate(templateId), [templateId]));

  const [validateResult, setValidateResult] = useState<{ valid: boolean; errors: string[]; warnings: string[] } | null>(null);

  async function handlePublish() { if (await publishAction.execute()) refetch(); }
  async function handleArchive() { if (await archiveAction.execute()) refetch(); }
  async function handleClone() {
    const res = await cloneAction.execute();
    if (res) router.push(`/admin/service-setup/templates/${(res as SetupTemplateDetail).id}`);
  }
  async function handleDelete() {
    if (!confirm("Delete this template? This cannot be undone.")) return;
    if (await deleteAction.execute()) router.push("/admin/service-setup/templates");
  }
  async function handleValidate() {
    const res = await validateAction.execute();
    if (res) setValidateResult(res as { valid: boolean; errors: string[]; warnings: string[] });
  }

  if (loading) return <div style={{ padding: "2rem", color: "var(--text-secondary)" }}>Loading...</div>;

  if (error) {
    return (
      <div style={{ padding: "2rem" }}>
        <p style={{ color: "var(--danger-text)", marginBottom: 12 }}>
          Could not load this template.
          {requestId ? ` Request ID: ${requestId}` : ""}
        </p>
        <Btn variant="secondary" size="sm" onClick={refetch}>Retry</Btn>
      </div>
    );
  }

  if (!template) return <div style={{ padding: "2rem", color: "var(--text-secondary)" }}>Template not found.</div>;

  const statusStyle = STATUS_STYLES[template.status] ?? STATUS_STYLES.draft;
  const itemsByModule: Record<string, typeof template.items> = {};
  for (const item of template.items ?? []) {
    (itemsByModule[item.module_key] ??= []).push(item);
  }

  return (
    <div style={{ padding: "1.5rem", maxWidth: 900 }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <Link href="/admin/service-setup/templates" style={{ color: "var(--text-tertiary)", fontSize: 13, textDecoration: "none" }}>
          ← Back to Templates
        </Link>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginTop: 8, flexWrap: "wrap", gap: 12 }}>
          <div>
            <h1 style={{ fontSize: "1.5rem", fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>{template.name}</h1>
            <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 6, flexWrap: "wrap" }}>
              <span style={{ fontFamily: "monospace", fontSize: 12, color: "var(--text-tertiary)" }}>{template.code}</span>
              <span style={{ fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 9999, textTransform: "uppercase", ...statusStyle }}>
                {template.status}
              </span>
              {template.is_system && (
                <span style={{ fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 9999, background: "var(--accent-muted)", color: "var(--accent)" }}>
                  System
                </span>
              )}
              <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{template.vertical_key} · {template.template_type} · v{template.version}</span>
            </div>
            {template.description && <p style={{ color: "var(--text-secondary)", marginTop: 8, fontSize: 14 }}>{template.description}</p>}
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Btn variant="ghost" size="sm" onClick={handleValidate} loading={validateAction.loading}>Validate</Btn>
            {template.status === "draft" && (
              <Btn variant="success" size="sm" onClick={handlePublish} loading={publishAction.loading}>Publish</Btn>
            )}
            {template.status === "published" && (
              <Btn variant="secondary" size="sm" onClick={handleArchive} loading={archiveAction.loading}>Archive</Btn>
            )}
            <Btn variant="secondary" size="sm" onClick={handleClone} loading={cloneAction.loading}>Clone</Btn>
            {template.status === "draft" && (
              <Btn variant="danger" size="sm" onClick={handleDelete} loading={deleteAction.loading}>Delete</Btn>
            )}
          </div>
        </div>
      </div>

      {validateResult && (
        <div style={{
          marginBottom: 24, borderRadius: 8, padding: 14,
          background: validateResult.valid ? "var(--success-bg)" : "var(--danger-bg)",
          border: `1px solid ${validateResult.valid ? "var(--success-border)" : "var(--danger-border)"}`,
        }}>
          <p style={{ margin: 0, fontSize: 13, fontWeight: 600, color: validateResult.valid ? "var(--success-text)" : "var(--danger-text)" }}>
            {validateResult.valid ? "✓ Template is valid." : "✗ Template has validation errors."}
          </p>
          {validateResult.errors?.map((e, i) => (
            <p key={i} style={{ fontSize: 12, color: "var(--danger-text)", margin: "4px 0 0" }}>⚠ {e}</p>
          ))}
          {validateResult.warnings?.map((w, i) => (
            <p key={i} style={{ fontSize: 12, color: "var(--warning-text)", margin: "4px 0 0" }}>ℹ {w}</p>
          ))}
        </div>
      )}

      {(publishAction.error || archiveAction.error || cloneAction.error || deleteAction.error) && (
        <p style={{ fontSize: 12, color: "var(--danger-text)", marginBottom: 16 }}>
          {publishAction.error || archiveAction.error || cloneAction.error || deleteAction.error}
        </p>
      )}

      {/* Modules */}
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontWeight: 700, fontSize: 15, margin: "0 0 10px", color: "var(--text-primary)" }}>
          Modules ({(template.modules ?? []).length})
        </h2>
        {(template.modules ?? []).length === 0 ? (
          <p style={{ color: "var(--text-tertiary)", fontSize: 13 }}>No modules configured.</p>
        ) : (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {template.modules.map(m => (
              <span key={m.id} style={{
                fontSize: 12, padding: "4px 10px", borderRadius: 9999,
                background: m.is_enabled ? "var(--accent-muted)" : "var(--surface-sunken)",
                color: m.is_enabled ? "var(--accent)" : "var(--text-tertiary)",
                border: "1px solid var(--border)",
              }}>
                {m.module_name || m.module_key}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Items */}
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontWeight: 700, fontSize: 15, margin: "0 0 10px", color: "var(--text-primary)" }}>
          Template Items ({(template.items ?? []).length})
        </h2>
        {(template.items ?? []).length === 0 ? (
          <p style={{ color: "var(--text-tertiary)", fontSize: 13 }}>
            No items yet. Edit this template from the Templates list to add content.
          </p>
        ) : (
          Object.entries(itemsByModule).map(([moduleKey, moduleItems]) => (
            <div key={moduleKey} style={{ marginBottom: 16, border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden" }}>
              <div style={{ padding: "8px 14px", background: "var(--surface-sunken)", fontWeight: 600, fontSize: 13, color: "var(--text-primary)" }}>
                {moduleKey.replace(/_/g, " ")} <span style={{ fontWeight: 400, color: "var(--text-tertiary)" }}>({moduleItems.length})</span>
              </div>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <tbody>
                  {moduleItems.map(item => (
                    <tr key={item.id} style={{ borderTop: "1px solid var(--border)" }}>
                      <td style={{ padding: "8px 14px", color: "var(--text-primary)" }}>{item.item_name}</td>
                      <td style={{ padding: "8px 14px", fontFamily: "monospace", fontSize: 11, color: "var(--text-tertiary)" }}>{item.item_key}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))
        )}
      </div>

      {/* Apply hint */}
      <div style={{ background: "var(--surface-sunken)", border: "1px solid var(--border)", borderRadius: 8, padding: 16 }}>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 10px" }}>
          To launch a category or service using this template, select it in Step 2 of the Bulk Setup Wizard.
        </p>
        <Btn variant="secondary" size="sm" onClick={() => router.push("/admin/service-setup/bulk-wizard")}>
          Go to Bulk Setup Wizard
        </Btn>
      </div>
    </div>
  );
}
