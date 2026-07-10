"use client";
import React, { useState, use, useCallback } from "react";
import { MapPin, Wrench, Users, GitMerge, ArrowLeft, CheckCircle, XCircle, Archive, Trash2, Plus, ChevronDown, ChevronRight } from "lucide-react";
import { AdminLayout } from "../../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Modal, Input } from "../../../../../components/shared/ui";
import { catalogApi, type Brand34D, type ServiceCategory, type MasterService } from "../../../../../lib/api";
import { useApi, useAction } from "../../../../../hooks/useApi";

type DetailTab = "overview" | "category-availability" | "service-availability" | "merge";
const TABS: { id: DetailTab; label: string }[] = [
  { id: "overview",              label: "Overview" },
  { id: "category-availability", label: "Category Availability" },
  { id: "service-availability",  label: "Service Availability" },
  { id: "merge",                 label: "Merge / Aliases" },
];

export default function BrandDetailPage({ params }: { params: Promise<{ brand_id: string }> }) {
  const { brand_id } = use(params);
  const [activeTab, setActiveTab] = useState<DetailTab>("overview");
  const [showMerge, setShowMerge] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [targetBrandId, setTargetBrandId] = useState("");
  const [mergeNote, setMergeNote] = useState("");
  const [editName, setEditName] = useState("");
  const [editCode, setEditCode] = useState("");
  const [editDesc, setEditDesc] = useState("");

  // Track in-flight toggles to prevent double-clicks
  const [pendingCatIds, setPendingCatIds] = useState<Set<string>>(new Set());
  const [pendingSvcIds, setPendingSvcIds] = useState<Set<string>>(new Set());

  // Expand/collapse service groups
  const [expandedCats, setExpandedCats] = useState<Set<string>>(new Set());

  const { data: brand, loading, error, refetch } = useApi(
    () => catalogApi.getBrand(brand_id),
    [brand_id],
  );

  const { data: catsData } = useApi(() => catalogApi.listCategories(true), []);
  const { data: svcsData } = useApi(() => catalogApi.listMasterServices(undefined, undefined, true), []);
  const allCategories = (catsData?.categories ?? []) as ServiceCategory[];
  const allServices   = (svcsData?.services   ?? []) as MasterService[];

  const activateAction   = useAction(async () => { await catalogApi.activateBrand(brand_id);   refetch(); });
  const deactivateAction = useAction(async () => { await catalogApi.deactivateBrand(brand_id); refetch(); });
  const archiveAction    = useAction(async () => { await catalogApi.archiveBrand(brand_id);    refetch(); });
  const mergeAction      = useAction(async () => {
    if (!targetBrandId.trim()) return;
    await catalogApi.mergeBrand(brand_id, targetBrandId.trim(), mergeNote || undefined);
    setShowMerge(false);
    window.location.href = `/admin/service-setup/brands/${targetBrandId.trim()}`;
  });
  const updateAction = useAction(async () => {
    await catalogApi.updateBrand(brand_id, {
      name: editName || undefined, code: editCode || undefined, description: editDesc || undefined,
    });
    setShowEdit(false); refetch();
  });

  const b = brand as Brand34D | undefined;

  // Current mappings as sets (for O(1) lookup)
  const mappedCatIds = new Set((b?.category_mappings ?? []).map((m: any) => m.category_id as string));
  const mappedSvcIds = new Set((b?.service_mappings   ?? []).map((m: any) => m.service_id  as string));

  async function toggleCategory(catId: string, isMapped: boolean) {
    if (pendingCatIds.has(catId)) return;
    setPendingCatIds(p => new Set(p).add(catId));
    try {
      if (isMapped) {
        await catalogApi.unmapBrandCategory(brand_id, catId);
      } else {
        if (b?.status !== "active") {
          alert("Activate brand before mapping to categories.");
          return;
        }
        await catalogApi.mapBrandCategories(brand_id, [catId]);
      }
      refetch();
    } finally {
      setPendingCatIds(p => { const n = new Set(p); n.delete(catId); return n; });
    }
  }

  async function toggleService(svcId: string, isMapped: boolean) {
    if (pendingSvcIds.has(svcId)) return;
    setPendingSvcIds(p => new Set(p).add(svcId));
    try {
      if (isMapped) {
        await catalogApi.unmapBrandService(brand_id, svcId);
      } else {
        if (b?.status !== "active") {
          alert("Activate brand before mapping to services.");
          return;
        }
        await catalogApi.mapBrandServices(brand_id, [svcId]);
      }
      refetch();
    } finally {
      setPendingSvcIds(p => { const n = new Set(p); n.delete(svcId); return n; });
    }
  }

  function toggleCatExpand(catId: string) {
    setExpandedCats(p => {
      const n = new Set(p);
      n.has(catId) ? n.delete(catId) : n.add(catId);
      return n;
    });
  }

  function statusBadge(s?: string) {
    if (!s) return null;
    const map: Record<string, string> = { active: "success", inactive: "warning", archived: "default", deprecated: "error" };
    return <Badge variant={(map[s] as any) ?? "default"}>{s.replace("_", " ")}</Badge>;
  }

  if (loading) return <AdminLayout><div style={{ padding: 40, textAlign: "center" }}>Loading…</div></AdminLayout>;
  if (error || !b) return (
    <AdminLayout>
      <div style={{ padding: 40, color: "var(--error)" }}>
        {error ?? "Brand not found."}
        <Btn variant="ghost" onClick={() => window.history.back()} style={{ marginLeft: 12 }}>
          <ArrowLeft size={13} /> Back
        </Btn>
      </div>
    </AdminLayout>
  );

  // Services grouped by category
  const servicesByCategory = allCategories.map(cat => ({
    cat,
    services: allServices.filter(s => (s as any).category_id === (cat as any).category_id),
  })).filter(g => g.services.length > 0);

  const mappedCatCount = mappedCatIds.size;
  const mappedSvcCount = mappedSvcIds.size;

  return (
    <AdminLayout>
      <div style={{ padding: "24px 32px", maxWidth: 1100, margin: "0 auto" }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
          <Btn variant="ghost" size="sm" onClick={() => window.location.href = "/admin/service-setup/brands"}>
            <ArrowLeft size={14} />
          </Btn>
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>{b.name}</h1>
              {statusBadge(b.status)}
              {b.is_global && <Badge variant="info">Global</Badge>}
            </div>
            <div style={{ fontSize: 13, opacity: 0.5, marginTop: 2 }}>
              {b.code && <span style={{ marginRight: 12 }}>{b.code}</span>}
              {b.country_of_origin && <span>{b.country_of_origin}</span>}
            </div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <Btn size="sm" variant="secondary" onClick={() => { setEditName(b.name); setEditCode(b.code ?? ""); setEditDesc(b.description ?? ""); setShowEdit(true); }}>
              Edit
            </Btn>
            {b.status === "active" ? (
              <Btn size="sm" variant="ghost" onClick={() => deactivateAction.execute()}>
                <XCircle size={13} style={{ marginRight: 4 }} /> Deactivate
              </Btn>
            ) : b.status === "inactive" ? (
              <Btn size="sm" variant="ghost" onClick={() => activateAction.execute()}>
                <CheckCircle size={13} style={{ marginRight: 4 }} /> Activate
              </Btn>
            ) : null}
            {b.status !== "archived" && (
              <Btn size="sm" variant="ghost" onClick={() => {
                if (confirm("Archive this brand?")) archiveAction.execute();
              }}>
                <Archive size={13} style={{ marginRight: 4 }} /> Archive
              </Btn>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 2, marginBottom: 20, borderBottom: "1px solid var(--border)" }}>
          {TABS.map(t => (
            <button key={t.id} onClick={() => setActiveTab(t.id)} style={{
              padding: "8px 16px", fontSize: 13, border: "none", background: "none", cursor: "pointer",
              color: activeTab === t.id ? "var(--primary)" : "var(--text-muted)",
              borderBottom: activeTab === t.id ? "2px solid var(--primary)" : "2px solid transparent",
              fontWeight: activeTab === t.id ? 600 : 400,
            }}>{t.label}</button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === "overview" && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <Card>
              <div style={{ padding: 16 }}>
                <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Brand Info</h3>
                <dl style={{ display: "grid", gridTemplateColumns: "130px 1fr", gap: "6px 12px", fontSize: 13 }}>
                  <dt style={{ opacity: 0.5 }}>Name</dt><dd style={{ margin: 0 }}>{b.name}</dd>
                  <dt style={{ opacity: 0.5 }}>Display Name</dt><dd style={{ margin: 0 }}>{b.display_name}</dd>
                  <dt style={{ opacity: 0.5 }}>Code</dt><dd style={{ margin: 0 }}>{b.code || "—"}</dd>
                  <dt style={{ opacity: 0.5 }}>Slug</dt><dd style={{ margin: 0, fontSize: 11, fontFamily: "monospace" }}>{b.slug}</dd>
                  <dt style={{ opacity: 0.5 }}>Status</dt><dd style={{ margin: 0 }}>{statusBadge(b.status)}</dd>
                  <dt style={{ opacity: 0.5 }}>Scope</dt><dd style={{ margin: 0 }}>{b.is_global ? "Global brand" : "Category-specific"}</dd>
                  <dt style={{ opacity: 0.5 }}>Country</dt><dd style={{ margin: 0 }}>{b.country_of_origin || "—"}</dd>
                  <dt style={{ opacity: 0.5 }}>Website</dt><dd style={{ margin: 0 }}>
                    {b.website_url ? <a href={b.website_url} target="_blank" rel="noopener noreferrer" style={{ color: "var(--primary)" }}>{b.website_url}</a> : "—"}
                  </dd>
                  <dt style={{ opacity: 0.5 }}>Description</dt><dd style={{ margin: 0 }}>{b.description || "—"}</dd>
                </dl>
              </div>
            </Card>
            <Card>
              <div style={{ padding: 16 }}>
                <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Visibility Summary</h3>
                <p style={{ fontSize: 12, opacity: 0.6, marginBottom: 12 }}>
                  This brand is visible only where explicitly mapped. Creating a brand once does not make it visible everywhere.
                </p>
                <div style={{ display: "flex", gap: 16 }}>
                  {[
                    { label: "Categories", value: mappedCatCount, icon: <MapPin size={14} />, tab: "category-availability" as DetailTab },
                    { label: "Services",   value: mappedSvcCount, icon: <Wrench size={14} />, tab: "service-availability"  as DetailTab },
                    { label: "Providers",  value: b.provider_usage_count ?? 0, icon: <Users size={14} />, tab: null },
                  ].map(item => (
                    <div key={item.label} onClick={() => item.tab && setActiveTab(item.tab)}
                      style={{ flex: 1, background: "var(--surface-raised, #f8fafc)", borderRadius: 8, padding: "12px 16px", textAlign: "center", cursor: item.tab ? "pointer" : "default" }}>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6, marginBottom: 4, opacity: 0.6 }}>
                        {item.icon} <span style={{ fontSize: 12 }}>{item.label}</span>
                      </div>
                      <div style={{ fontSize: 24, fontWeight: 700 }}>{item.value}</div>
                      {item.tab && <div style={{ fontSize: 11, opacity: 0.4, marginTop: 2 }}>click to manage</div>}
                    </div>
                  ))}
                </div>
                {b.status !== "active" && (
                  <div style={{ marginTop: 12, padding: 10, background: "var(--warning-bg, #fff8e1)", borderRadius: 6, fontSize: 12 }}>
                    Brand is <strong>{b.status}</strong> — activate it to enable new mappings.
                  </div>
                )}
              </div>
            </Card>
          </div>
        )}

        {/* Category Availability Tab */}
        {activeTab === "category-availability" && (
          <Card>
            <div style={{ padding: 16, borderBottom: "1px solid var(--border)" }}>
              <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>
                Category Availability
                <span style={{ marginLeft: 10, fontSize: 12, fontWeight: 400, opacity: 0.5 }}>
                  {mappedCatCount}/{allCategories.length} categories
                </span>
              </h3>
              <p style={{ fontSize: 12, opacity: 0.6, margin: "6px 0 0" }}>
                Toggle to control which categories this brand appears in. A brand only appears in categories you explicitly enable here.
              </p>
            </div>
            {allCategories.length === 0 && (
              <div style={{ padding: 32, textAlign: "center", opacity: 0.5 }}>No categories found.</div>
            )}
            {allCategories.map(cat => {
              const catId = (cat as any).category_id as string;
              const isMapped = mappedCatIds.has(catId);
              const isPending = pendingCatIds.has(catId);
              return (
                <div key={catId} style={{ display: "flex", alignItems: "center", gap: 14, padding: "12px 16px", borderBottom: "1px solid var(--border)", opacity: isPending ? 0.6 : 1 }}>
                  <button
                    disabled={isPending}
                    onClick={() => toggleCategory(catId, isMapped)}
                    style={{
                      width: 36, height: 20, borderRadius: 10, border: "none", cursor: isPending ? "wait" : "pointer",
                      background: isMapped ? "var(--primary, #3b82f6)" : "var(--border, #e5e7eb)",
                      position: "relative", transition: "background 0.2s", flexShrink: 0,
                    }}
                    aria-label={isMapped ? "Unmap" : "Map"}
                  >
                    <span style={{
                      position: "absolute", top: 2, left: isMapped ? 18 : 2, width: 16, height: 16,
                      borderRadius: "50%", background: "#fff", transition: "left 0.2s",
                    }} />
                  </button>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: isMapped ? 600 : 400 }}>{cat.name}</div>
                    {(cat as any).description && (
                      <div style={{ fontSize: 11, opacity: 0.5 }}>{(cat as any).description}</div>
                    )}
                  </div>
                  {isMapped ? (
                    <Badge variant="success">Mapped</Badge>
                  ) : (
                    <span style={{ fontSize: 11, opacity: 0.4 }}>Not mapped</span>
                  )}
                </div>
              );
            })}
          </Card>
        )}

        {/* Service Availability Tab */}
        {activeTab === "service-availability" && (
          <div>
            <div style={{ marginBottom: 12, padding: "10px 14px", background: "var(--surface-raised, #f8fafc)", borderRadius: 8, fontSize: 12, opacity: 0.7 }}>
              <strong>{mappedSvcCount}</strong> services mapped. Brand is available only in mapped services — providers will only see it when offering those specific services.
            </div>
            {servicesByCategory.map(({ cat, services }) => {
              const catId = (cat as any).category_id as string;
              const isCatMapped = mappedCatIds.has(catId);
              const catSvcMappedCount = services.filter(s => mappedSvcIds.has((s as any).service_id)).length;
              const isExpanded = expandedCats.has(catId) || catSvcMappedCount > 0;

              return (
                <Card key={catId} style={{ marginBottom: 12 }}>
                  <div
                    onClick={() => toggleCatExpand(catId)}
                    style={{ padding: "12px 16px", display: "flex", alignItems: "center", gap: 10, cursor: "pointer", borderBottom: isExpanded ? "1px solid var(--border)" : "none" }}
                  >
                    {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{cat.name}</span>
                    {isCatMapped && <Badge variant="success">Category mapped</Badge>}
                    <span style={{ marginLeft: "auto", fontSize: 12, opacity: 0.5 }}>
                      {catSvcMappedCount}/{services.length} services
                    </span>
                  </div>
                  {isExpanded && (
                    <div>
                      {services.map(svc => {
                        const svcId = (svc as any).service_id as string;
                        const isMapped = mappedSvcIds.has(svcId);
                        const isPending = pendingSvcIds.has(svcId);
                        return (
                          <div key={svcId} style={{ display: "flex", alignItems: "center", gap: 14, padding: "10px 16px 10px 36px", borderBottom: "1px solid var(--border)", opacity: isPending ? 0.6 : 1 }}>
                            <button
                              disabled={isPending}
                              onClick={() => toggleService(svcId, isMapped)}
                              style={{
                                width: 36, height: 20, borderRadius: 10, border: "none", cursor: isPending ? "wait" : "pointer",
                                background: isMapped ? "var(--primary, #3b82f6)" : "var(--border, #e5e7eb)",
                                position: "relative", transition: "background 0.2s", flexShrink: 0,
                              }}
                              aria-label={isMapped ? "Unmap" : "Map"}
                            >
                              <span style={{
                                position: "absolute", top: 2, left: isMapped ? 18 : 2, width: 16, height: 16,
                                borderRadius: "50%", background: "#fff", transition: "left 0.2s",
                              }} />
                            </button>
                            <div style={{ flex: 1 }}>
                              <span style={{ fontSize: 13, fontWeight: isMapped ? 600 : 400 }}>{svc.service_name}</span>
                              <span style={{ marginLeft: 8, fontSize: 11, padding: "2px 6px", background: "var(--surface-raised, #f0f0f0)", borderRadius: 4 }}>
                                {svc.job_type}
                              </span>
                            </div>
                            {isMapped ? (
                              <Badge variant="success">Available</Badge>
                            ) : (
                              <span style={{ fontSize: 11, opacity: 0.4 }}>Hidden from providers</span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </Card>
              );
            })}
            {servicesByCategory.length === 0 && (
              <Card><div style={{ padding: 32, textAlign: "center", opacity: 0.5 }}>No active services found.</div></Card>
            )}
          </div>
        )}

        {/* Merge Tab */}
        {activeTab === "merge" && (
          <Card>
            <div style={{ padding: 16 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Merge / Alias Management</h3>
              <p style={{ fontSize: 13, opacity: 0.6, marginBottom: 16 }}>
                Merge this brand into another canonical brand. All category mappings, service mappings, and provider support records will be moved. This brand will be archived.
              </p>
              <Btn onClick={() => setShowMerge(true)} variant="secondary">
                <GitMerge size={13} style={{ marginRight: 4 }} /> Merge into another brand
              </Btn>
              {b.replacement_brand_id && (
                <div style={{ marginTop: 12, padding: 12, background: "var(--warning-bg, #fff8e1)", borderRadius: 6, fontSize: 13 }}>
                  This brand was merged. Replacement: <code>{b.replacement_brand_id}</code>
                </div>
              )}
            </div>
          </Card>
        )}

        {/* Merge Modal */}
        <Modal open={showMerge} onClose={() => setShowMerge(false)} title="Merge Brand">
          <p style={{ fontSize: 13, opacity: 0.6, marginBottom: 12 }}>
            Enter the UUID of the canonical brand to merge <strong>{b.name}</strong> into.
          </p>
          <Input label="Target Brand UUID *" value={targetBrandId}
            onChange={v => setTargetBrandId(v)} placeholder="canonical-brand-uuid" />
          <Input label="Admin Note" value={mergeNote}
            onChange={v => setMergeNote(v)} placeholder="Reason for merge…" />
          {mergeAction.error && <div style={{ color: "var(--error)", fontSize: 13 }}>{mergeAction.error}</div>}
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
            <Btn variant="ghost" onClick={() => setShowMerge(false)}>Cancel</Btn>
            <Btn disabled={!targetBrandId.trim() || mergeAction.loading}
              onClick={() => { if (confirm("Merge and archive this brand?")) mergeAction.execute(); }}>
              {mergeAction.loading ? "Merging…" : "Merge Brand"}
            </Btn>
          </div>
        </Modal>

        {/* Edit Modal */}
        <Modal open={showEdit} onClose={() => setShowEdit(false)} title="Edit Brand">
          <Input label="Name" value={editName} onChange={v => setEditName(v)} />
          <Input label="Code" value={editCode} onChange={v => setEditCode(v.toUpperCase())} />
          <Input label="Description" value={editDesc} onChange={v => setEditDesc(v)} />
          {updateAction.error && <div style={{ color: "var(--error)", fontSize: 13 }}>{updateAction.error}</div>}
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
            <Btn variant="ghost" onClick={() => setShowEdit(false)}>Cancel</Btn>
            <Btn disabled={updateAction.loading} onClick={() => updateAction.execute()}>
              {updateAction.loading ? "Saving…" : "Save"}
            </Btn>
          </div>
        </Modal>
      </div>
    </AdminLayout>
  );
}
