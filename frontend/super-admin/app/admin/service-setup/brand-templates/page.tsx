"use client";
import React, { useState } from "react";
import { Layers, Plus, Zap } from "lucide-react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Modal, Input, DataTable, SectionHeader } from "../../../../components/shared/ui";
import { catalogApi, type BrandTemplate34D } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";

export default function BrandTemplatesPage() {
  const [showCreate, setShowCreate] = useState(false);
  const [showApply, setShowApply] = useState<BrandTemplate34D | null>(null);
  const [form, setForm] = useState({ code: "", name: "", description: "", brand_ids: "", vertical_type: "" });
  const [serviceIds, setServiceIds] = useState("");

  const { data, loading, refetch } = useApi(() => catalogApi.listBrandTemplates(), []);

  const createAction = useAction(async () => {
    const brand_ids = form.brand_ids.split(/[\s,]+/).filter(Boolean);
    await catalogApi.createBrandTemplate({ code: form.code, name: form.name, brand_ids, vertical_type: form.vertical_type || undefined });
    setShowCreate(false);
    setForm({ code: "", name: "", description: "", brand_ids: "", vertical_type: "" });
    refetch();
  });

  const applyAction = useAction(async (templateId: string) => {
    const svcIds = serviceIds.split(/[\s,]+/).filter(Boolean);
    await catalogApi.applyBrandTemplate(templateId, svcIds.length ? svcIds : undefined);
    setShowApply(null);
    setServiceIds("");
  });

  const templates = data?.templates ?? [];

  return (
    <AdminLayout>
      <div style={{ padding: "24px 32px", maxWidth: 1100, margin: "0 auto" }}>
        <SectionHeader
          title="Brand Templates"
          subtitle="Reusable brand starter packs — apply in bulk to services"
          icon={<Layers size={20} />}
          actions={
            <div style={{ display: "flex", gap: 8 }}>
              <Btn size="sm" variant="ghost" onClick={() => window.location.href = "/admin/service-setup/brands"}>
                ← All Brands
              </Btn>
              <Btn size="sm" onClick={() => setShowCreate(true)}>
                <Plus size={13} style={{ marginRight: 4 }} /> New Template
              </Btn>
            </div>
          }
        />

        <Card>
          {loading && <div style={{ padding: 24, textAlign: "center", opacity: 0.5 }}>Loading…</div>}
          {!loading && templates.length === 0 && (
            <div style={{ padding: 40, textAlign: "center", opacity: 0.5 }}>No templates yet. Create a starter pack to bulk-map brands to services.</div>
          )}
          {!loading && templates.length > 0 && (
            <DataTable
              columns={[
                { key: "name", label: "Template", render: (v: unknown, row: Record<string,unknown>) => {
                  const r = row as unknown as BrandTemplate34D;
                  return (
                    <div>
                      <div style={{ fontWeight: 500 }}>{v as string}</div>
                      <div style={{ fontSize: 11, opacity: 0.5 }}>{r.code} {r.vertical_type ? `· ${r.vertical_type}` : ""}</div>
                    </div>
                  );
                }},
                { key: "status", label: "Status", render: (v: unknown) => (
                  <Badge variant={(v as string) === "active" ? "success" : "default"}>{v as string}</Badge>
                )},
                { key: "items", label: "Brands", render: (items: unknown) => {
                  const arr = (items as BrandTemplate34D["items"]) ?? [];
                  return (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                      {arr.slice(0, 5).map(i => (
                        <Badge key={i.brand_id} variant="default">{i.brand_name}</Badge>
                      ))}
                      {arr.length > 5 && <Badge variant="default">+{arr.length - 5} more</Badge>}
                    </div>
                  );
                }},
                { key: "actions", label: "", render: (_: unknown, row: Record<string,unknown>) => (
                  <Btn size="sm" onClick={() => { setShowApply(row as unknown as BrandTemplate34D); setServiceIds(""); }}>
                    <Zap size={12} style={{ marginRight: 3 }} /> Apply
                  </Btn>
                )},
              ]}
              rows={templates as unknown as Record<string,unknown>[]}
            />
          )}
        </Card>

        {/* Create Template Modal */}
        <Modal open={showCreate} onClose={() => setShowCreate(false)} title="New Brand Template">
          <Input label="Code (e.g. AC_BRANDS) *" value={form.code}
            onChange={v => setForm(f => ({ ...f, code: v.toUpperCase() }))} />
          <Input label="Name *" value={form.name}
            onChange={v => setForm(f => ({ ...f, name: v }))} />
          <Input label="Vertical Type (e.g. home_services)" value={form.vertical_type}
            onChange={v => setForm(f => ({ ...f, vertical_type: v }))} />
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 12, opacity: 0.6, display: "block", marginBottom: 4 }}>Brand UUIDs (comma/newline separated) *</label>
            <textarea
              value={form.brand_ids}
              onChange={e => setForm(f => ({ ...f, brand_ids: e.target.value }))}
              placeholder="brand-uuid-1, brand-uuid-2, ..."
              style={{ width: "100%", height: 80, fontSize: 12, fontFamily: "monospace", padding: 8, border: "1px solid var(--border)", borderRadius: 6, resize: "vertical", background: "var(--surface)", color: "var(--text)" }}
            />
          </div>
          {createAction.error && <div style={{ color: "var(--error)", fontSize: 13 }}>{createAction.error}</div>}
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <Btn variant="ghost" onClick={() => setShowCreate(false)}>Cancel</Btn>
            <Btn disabled={!form.code || !form.name || !form.brand_ids || createAction.loading}
              onClick={() => createAction.execute()}>
              {createAction.loading ? "Creating…" : "Create Template"}
            </Btn>
          </div>
        </Modal>

        {/* Apply Template Modal */}
        <Modal open={!!showApply} onClose={() => setShowApply(null)} title={`Apply: ${showApply?.name}`}>
          <p style={{ fontSize: 13, opacity: 0.6, marginBottom: 12 }}>
            Apply this template to map all its brands to the specified services.
            Leave empty to apply to all services in the template&apos;s category.
          </p>
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 12, opacity: 0.6, display: "block", marginBottom: 4 }}>Service UUIDs (optional)</label>
            <textarea
              value={serviceIds}
              onChange={e => setServiceIds(e.target.value)}
              placeholder="Leave empty for category-wide apply, or enter specific service UUIDs…"
              style={{ width: "100%", height: 80, fontSize: 12, fontFamily: "monospace", padding: 8, border: "1px solid var(--border)", borderRadius: 6, resize: "vertical", background: "var(--surface)", color: "var(--text)" }}
            />
          </div>
          {applyAction.error && <div style={{ color: "var(--error)", fontSize: 13 }}>{applyAction.error}</div>}
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <Btn variant="ghost" onClick={() => setShowApply(null)}>Close</Btn>
            <Btn disabled={applyAction.loading} onClick={() => showApply && applyAction.execute(showApply.template_id)}>
              {applyAction.loading ? "Applying…" : "Apply Template"}
            </Btn>
          </div>
        </Modal>
      </div>
    </AdminLayout>
  );
}
