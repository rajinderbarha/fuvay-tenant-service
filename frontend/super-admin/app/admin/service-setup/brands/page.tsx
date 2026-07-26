"use client";
import React, { useState, useCallback } from "react";
import { Tag, Plus, Search, CheckCircle, XCircle, Archive, GitMerge, ChevronRight } from "lucide-react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Modal, Input, Select, DataTable, SectionHeader } from "../../../../components/shared/ui";
import { catalogApi, type Brand34D, type BrandDuplicateWarning } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
  { value: "archived", label: "Archived" },
  { value: "deprecated", label: "Deprecated" },
  { value: "pending_review", label: "Pending Review" },
];

function statusBadge(s: string) {
  const map: Record<string, string> = {
    active: "success", inactive: "warning", archived: "default",
    deprecated: "error", pending_review: "info", rejected: "error",
  };
  return <Badge variant={(map[s] as any) ?? "default"}>{s.replace("_", " ")}</Badge>;
}

export default function AdminBrandsPage() {
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);
  const [duplicateWarning, setDuplicateWarning] = useState<BrandDuplicateWarning | null>(null);
  const [createForm, setCreateForm] = useState<{
    name: string; code: string; display_name: string; description: string;
    country_of_origin: string; website_url: string; is_global: boolean;
  }>({ name: "", code: "", display_name: "", description: "", country_of_origin: "", website_url: "", is_global: true });

  const { data: brandsData, loading, error, refetch } = useApi(
    () => catalogApi.listBrands({ status: filterStatus || undefined, search: search || undefined, page, page_size: 50 }),
    [filterStatus, search, page],
  );

  const createAction = useAction(async (force: boolean = false) => {
    const result = await catalogApi.createBrand({ ...createForm, force });
    if ("warning" in result && result.warning === "BRAND_DUPLICATE_POSSIBLE") {
      setDuplicateWarning(result as BrandDuplicateWarning);
      return;
    }
    setShowCreate(false);
    setDuplicateWarning(null);
    setCreateForm({ name: "", code: "", display_name: "", description: "", country_of_origin: "", website_url: "", is_global: true });
    refetch();
  });

  const activateAction = useAction(async (brandId: string) => {
    await catalogApi.activateBrand(brandId);
    refetch();
  });

  const deactivateAction = useAction(async (brandId: string) => {
    await catalogApi.deactivateBrand(brandId);
    refetch();
  });

  const brands = brandsData?.brands ?? [];
  const total = brandsData?.total ?? 0;

  return (
    <AdminLayout>
      <div style={{ padding: "24px 32px", maxWidth: 1280, margin: "0 auto" }}>
        <SectionHeader
          title="Brand Management"
          subtitle={`${total} brands · platform-controlled, provider-selectable`}
          icon={<Tag size={20} />}
          actions={
            <Btn size="sm" onClick={() => setShowCreate(true)}>
              <Plus size={14} style={{ marginRight: 4 }} /> New Brand
            </Btn>
          }
        />

        {/* Filters */}
        <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
          <div style={{ position: "relative", flex: 1 }}>
            <Search size={14} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", opacity: 0.4 }} />
            <input
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(1); }}
              placeholder="Search brands…"
              style={{ width: "100%", paddingLeft: 32, paddingRight: 12, paddingTop: 8, paddingBottom: 8, border: "1px solid var(--border)", borderRadius: 6, fontSize: 13, background: "var(--surface)", color: "var(--text)" }}
            />
          </div>
          <Select
            value={filterStatus}
            onChange={v => { setFilterStatus(v); setPage(1); }}
            options={STATUS_OPTIONS}
          />
          <Btn size="sm" variant="ghost" onClick={() => { refetch(); }}>Refresh</Btn>
          <Btn size="sm" variant="secondary" onClick={() => window.location.href = "/admin/service-setup/brand-requests"}>
            Brand Requests
          </Btn>
          <Btn size="sm" variant="secondary" onClick={() => window.location.href = "/admin/service-setup/brand-templates"}>
            Templates
          </Btn>
        </div>

        {/* Brands table */}
        <Card>
          {error && <div style={{ color: "var(--error)", padding: 16 }}>{error}</div>}
          {loading && <div style={{ padding: 24, textAlign: "center", opacity: 0.5 }}>Loading brands…</div>}
          {!loading && brands.length === 0 && (
            <div style={{ padding: 40, textAlign: "center", opacity: 0.5 }}>
              No brands found. Create your first brand to get started.
            </div>
          )}
          {!loading && brands.length > 0 && (
            <DataTable
              columns={[
                { key: "name", label: "Brand", render: (_: unknown, row: Record<string,unknown>) => {
                  const r = row as unknown as Brand34D;
                  return (
                    <div>
                      <div style={{ fontWeight: 500 }}>{r.name}</div>
                      {r.code && <div style={{ fontSize: 11, opacity: 0.5 }}>{r.code}</div>}
                      {r.country_of_origin && <div style={{ fontSize: 11, opacity: 0.4 }}>{r.country_of_origin}</div>}
                    </div>
                  );
                }},
                { key: "status", label: "Status", render: (v: unknown) => statusBadge(v as string) },
                { key: "category_mapping_count", label: "Categories", render: (v: unknown) => (
                  <span style={{ fontSize: 12 }}>{((v as number) ?? 0)} mapped</span>
                )},
                { key: "service_mapping_count", label: "Services", render: (v: unknown) => (
                  <span style={{ fontSize: 12 }}>{((v as number) ?? 0)} mapped</span>
                )},
                { key: "provider_usage_count", label: "Providers", render: (v: unknown) => (
                  <span style={{ fontSize: 12 }}>{((v as number) ?? 0)} using</span>
                )},
                { key: "is_global", label: "Scope", render: (v: unknown) => (
                  <span style={{ fontSize: 11, opacity: 0.6 }}>{(v as boolean) ? "Global" : "Regional"}</span>
                )},
                { key: "actions", label: "", render: (_: unknown, row: Record<string,unknown>) => {
                  const r = row as unknown as Brand34D;
                  return (
                    <div style={{ display: "flex", gap: 6 }}>
                      <Btn size="sm" variant="ghost" onClick={() => {
                        window.location.href = `/admin/service-setup/brands/${r.brand_id}`;
                      }}>
                        <ChevronRight size={13} />
                      </Btn>
                      {r.status === "active" ? (
                        <Btn size="sm" variant="ghost"
                          onClick={() => deactivateAction.execute(r.brand_id)}>
                          <XCircle size={13} />
                        </Btn>
                      ) : r.status === "inactive" ? (
                        <Btn size="sm" variant="ghost"
                          onClick={() => activateAction.execute(r.brand_id)}>
                          <CheckCircle size={13} />
                        </Btn>
                      ) : null}
                    </div>
                  );
                }},
              ]}
              rows={brands as unknown as Record<string,unknown>[]}
            />
          )}
        </Card>

        {/* Pagination */}
        {total > 50 && (
          <div style={{ display: "flex", gap: 8, justifyContent: "center", marginTop: 16 }}>
            <Btn size="sm" variant="secondary" disabled={page === 1} onClick={() => setPage(p => p - 1)}>Prev</Btn>
            <span style={{ fontSize: 13, padding: "6px 12px" }}>Page {page}</span>
            <Btn size="sm" variant="secondary" disabled={brands.length < 50} onClick={() => setPage(p => p + 1)}>Next</Btn>
          </div>
        )}

        {/* Create Brand Modal */}
        <Modal open={showCreate} onClose={() => { setShowCreate(false); setDuplicateWarning(null); }} title="New Brand">
          {duplicateWarning && (
            <div style={{ background: "var(--warning-bg, #fff8e1)", border: "1px solid var(--warning, var(--warning))", borderRadius: 6, padding: 12, marginBottom: 16 }}>
              <div style={{ fontWeight: 600, marginBottom: 6, color: "var(--warning, #b45309)" }}>
                Possible duplicate detected
              </div>
              <div style={{ fontSize: 13, marginBottom: 8 }}>{duplicateWarning.message}</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 10 }}>
                {duplicateWarning.possible_duplicates.map(d => (
                  <Badge key={d.brand_id} variant="warning">{d.name}</Badge>
                ))}
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <Btn size="sm" variant="secondary" onClick={() => setDuplicateWarning(null)}>Cancel</Btn>
                <Btn size="sm" onClick={() => createAction.execute(true)}>Create Anyway (force)</Btn>
              </div>
            </div>
          )}
          {!duplicateWarning && (
            <>
              <Input label="Brand Name *" value={createForm.name}
                onChange={v => setCreateForm(f => ({ ...f, name: v }))} />
              <Input label="Code (e.g. SAMSUNG)" value={createForm.code}
                onChange={v => setCreateForm(f => ({ ...f, code: v.toUpperCase() }))} />
              <Input label="Display Name" value={createForm.display_name}
                onChange={v => setCreateForm(f => ({ ...f, display_name: v }))} />
              <Input label="Country of Origin" value={createForm.country_of_origin}
                onChange={v => setCreateForm(f => ({ ...f, country_of_origin: v }))} />
              <Input label="Website URL" value={createForm.website_url}
                onChange={v => setCreateForm(f => ({ ...f, website_url: v }))} />
              <Input label="Description" value={createForm.description}
                onChange={v => setCreateForm(f => ({ ...f, description: v }))} />
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer" }}>
                  <input type="checkbox" checked={createForm.is_global}
                    onChange={e => setCreateForm(f => ({ ...f, is_global: e.target.checked }))} />
                  Global brand (available to all categories)
                </label>
              </div>
              {createAction.error && (
                <div style={{ color: "var(--error)", fontSize: 13, marginBottom: 8 }}>
                  {createAction.error}
                </div>
              )}
              <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                <Btn variant="ghost" onClick={() => setShowCreate(false)}>Cancel</Btn>
                <Btn disabled={!createForm.name || createAction.loading}
                  onClick={() => createAction.execute(false)}>
                  {createAction.loading ? "Creating…" : "Create Brand"}
                </Btn>
              </div>
            </>
          )}
        </Modal>
      </div>
    </AdminLayout>
  );
}
