"use client";
/**
 * Global Services — platform-owned promotional service cards shown to every
 * customer nationwide (mobile app's fixed "Global Services" section),
 * independent of vertical/category/tenant serviceability. Deliberately NOT
 * built on ServiceCategory/MasterService -- activating a category implies
 * tenant fulfillment machinery (serviceability zones, provider matching,
 * job pipeline) this feature explicitly has none of. A customer's interest
 * becomes a Lead here; an admin follows up by phone.
 */
import { useCallback, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Plus, RefreshCw, Phone, Trash2, Pencil } from "lucide-react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, Badge, Btn, Input, DataTable, Skeleton, Modal, Pagination, SummaryCard } from "../../../components/shared/ui";
import { IconPicker } from "../../../components/shared/IconPicker";
import { globalServicesApi, type GlobalService, type GlobalServiceLead } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";

function dt(v?: string | null) {
  return v ? new Date(v).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "—";
}

const STATUS_VARIANT: Record<string, "success" | "warning" | "muted" | "info"> = {
  new: "info", contacted: "warning", converted: "success", closed: "muted",
};

export default function GlobalServicesPage() {
  return (
    <Suspense fallback={<Skeleton height={400} />}>
      <GlobalServicesWorkspace />
    </Suspense>
  );
}

function GlobalServicesWorkspace() {
  const router = useRouter();
  const params = useSearchParams();
  const tab = (params.get("tab") as "services" | "leads") || "services";

  function setTab(t: "services" | "leads") {
    router.replace(`/admin/global-services?tab=${t}`);
  }

  return (
    <AdminLayout activeNav="global-services">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, margin: 0 }}>Global Services</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>
            Promotional services shown to every customer nationwide. No booking or provider assignment here —
            customer interest becomes a lead you call back.
          </p>
        </div>
        <Badge variant="info">Nationwide · Not zipcode-gated</Badge>
      </div>

      <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)", margin: "16px 0" }}>
        {(["services", "leads"] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            style={{ padding: "10px 14px", fontSize: 13, fontWeight: 600, background: "none", border: "none",
              borderBottom: tab === t ? "2px solid var(--brand)" : "2px solid transparent",
              color: tab === t ? "var(--text-primary)" : "var(--text-tertiary)", cursor: "pointer" }}>
            {t === "services" ? "Services" : "Leads"}
          </button>
        ))}
      </div>

      {tab === "services" ? <ServicesTab /> : <LeadsTab />}
    </AdminLayout>
  );
}

// ── Services tab ──────────────────────────────────────────────────────────────

type FormState = { name: string; tagline: string; description: string; icon_url: string; display_order: number; is_active: boolean };
const BLANK: FormState = { name: "", tagline: "", description: "", icon_url: "", display_order: 0, is_active: true };

function ServicesTab() {
  const services = useApi(useCallback(() => globalServicesApi.listServices(true), []));
  const [modal, setModal] = useState<"none" | "create" | "edit">("none");
  const [editing, setEditing] = useState<GlobalService | null>(null);
  const [form, setForm] = useState<FormState>(BLANK);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);

  const notify = (msg: string, ok = true) => { setToast({ msg, ok }); setTimeout(() => setToast(null), 3000); };

  function setF<K extends keyof FormState>(k: K, v: FormState[K]) { setForm(p => ({ ...p, [k]: v })); }

  function openCreate() { setForm(BLANK); setModal("create"); }
  function openEdit(svc: GlobalService) {
    setForm({
      name: svc.name, tagline: svc.tagline ?? "", description: svc.description ?? "",
      icon_url: svc.icon_url ?? "", display_order: svc.display_order, is_active: svc.is_active,
    });
    setEditing(svc); setModal("edit");
  }

  const createAction = useAction(useCallback(async (data: FormState) => {
    await globalServicesApi.createService({
      name: data.name, tagline: data.tagline || undefined, description: data.description || undefined,
      icon_url: data.icon_url || undefined, display_order: data.display_order, is_active: data.is_active,
    });
    services.refetch(); setModal("none"); notify("Service created.");
  }, [services]));

  const updateAction = useAction(useCallback(async ({ id, data }: { id: string; data: FormState }) => {
    await globalServicesApi.updateService(id, {
      name: data.name, tagline: data.tagline || undefined, description: data.description || undefined,
      icon_url: data.icon_url || undefined, display_order: data.display_order, is_active: data.is_active,
    });
    services.refetch(); setModal("none"); notify("Service updated.");
  }, [services]));

  const deactivateAction = useAction(useCallback(async (id: string) => {
    await globalServicesApi.deactivateService(id);
    services.refetch(); notify("Service deactivated.");
  }, [services]));

  const items = services.data ?? [];

  return (
    <div>
      {toast && (
        <div style={{ marginBottom: 12, padding: "8px 12px", borderRadius: 8,
          background: toast.ok ? "var(--success-bg)" : "var(--danger-bg)",
          border: `1px solid ${toast.ok ? "var(--success-border)" : "var(--danger-border)"}` }}>
          <p style={{ fontSize: 12, margin: 0, color: toast.ok ? "var(--success-text)" : "var(--danger-text)" }}>{toast.msg}</p>
        </div>
      )}
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginBottom: 12 }}>
        <Btn variant="ghost" icon={<RefreshCw size={14} />} onClick={() => services.refetch()}>Refresh</Btn>
        <Btn variant="primary" icon={<Plus size={14} />} onClick={openCreate}>New Global Service</Btn>
      </div>

      {services.loading ? <Skeleton height={200} /> : items.length === 0 ? (
        <Card padding={24} style={{ textAlign: "center" }}>
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: 0 }}>
            No global services yet — create one to show it in the mobile app's fixed promotional section.
          </p>
        </Card>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 12 }}>
          {items.map(svc => (
            <Card key={svc.id} padding={16} style={{ opacity: svc.is_active ? 1 : 0.55 }}>
              <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                <div style={{ width: 44, height: 44, borderRadius: "var(--radius-lg)", background: "var(--surface-sunken)",
                  border: "1px solid var(--border)", flexShrink: 0, overflow: "hidden", display: "flex",
                  alignItems: "center", justifyContent: "center" }}>
                  {svc.icon_url
                    // eslint-disable-next-line @next/next/no-img-element
                    ? <img src={svc.icon_url} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                    : <span style={{ fontSize: 18 }}>🛠️</span>}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ fontSize: 14, fontWeight: 700, margin: 0 }}>{svc.name}</p>
                  {svc.tagline && <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "2px 0 0" }}>{svc.tagline}</p>}
                </div>
                <Badge variant={svc.is_active ? "success" : "muted"}>{svc.is_active ? "Active" : "Inactive"}</Badge>
              </div>
              {svc.description && (
                <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: "10px 0 0" }}>{svc.description}</p>
              )}
              <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                <Btn variant="ghost" size="sm" icon={<Pencil size={12} />} onClick={() => openEdit(svc)}>Edit</Btn>
                {svc.is_active && (
                  <Btn variant="ghost" size="sm" icon={<Trash2 size={12} />} onClick={() => deactivateAction.execute(svc.id)}
                    disabled={deactivateAction.loading} style={{ color: "var(--danger-text)" }}>
                    Deactivate
                  </Btn>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal open={modal !== "none"} onClose={() => setModal("none")} title={modal === "create" ? "New Global Service" : `Edit: ${editing?.name ?? ""}`} size="md">
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {(createAction.error || updateAction.error) && (
            <div style={{ padding: "10px 14px", borderRadius: 9, background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
              <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>{createAction.error ?? updateAction.error}</p>
            </div>
          )}
          <Input label="Name *" placeholder="e.g. Home Renovation Consultation" value={form.name} onChange={v => setF("name", v)} />
          <Input label="Tagline" placeholder="Short line shown on the card" value={form.tagline} onChange={v => setF("tagline", v)} />
          <div>
            <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Description</label>
            <textarea value={form.description} onChange={e => setF("description", e.target.value)} rows={3}
              placeholder="Shown when the customer opens this card"
              style={{ width: "100%", padding: "8px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)",
                background: "var(--bg)", color: "var(--text-primary)", fontSize: 13, boxSizing: "border-box",
                outline: "none", resize: "vertical", fontFamily: "inherit" }} />
          </div>
          <IconPicker label="Icon" context="global_service_icon" value={form.icon_url} onChange={v => setF("icon_url", v ?? "")} />
          <Input label="Display Order" type="number" value={String(form.display_order)} onChange={v => setF("display_order", Number(v) || 0)} />
          {modal === "edit" && (
            <label style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 13, cursor: "pointer" }}>
              <input type="checkbox" checked={form.is_active} onChange={e => setF("is_active", e.target.checked)} style={{ width: 15, height: 15 }} />
              Active (visible in the mobile app)
            </label>
          )}
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setModal("none")}>Cancel</Btn>
            <Btn variant="primary" size="sm" disabled={!form.name.trim()}
              loading={createAction.loading || updateAction.loading}
              onClick={() => modal === "create" ? createAction.execute(form) : editing && updateAction.execute({ id: editing.id, data: form })}>
              {modal === "create" ? "Create" : "Save Changes"}
            </Btn>
          </div>
        </div>
      </Modal>
    </div>
  );
}

// ── Leads tab ─────────────────────────────────────────────────────────────────

function LeadsTab() {
  const [status, setStatus] = useState<string | undefined>(undefined);
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<GlobalServiceLead | null>(null);

  const summary = useApi(useCallback(() => globalServicesApi.leadsSummary(), []));
  const leads = useApi(useCallback(() => globalServicesApi.listLeads({ status, page, page_size: 20 }), [status, page]));

  const s = summary.data;

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12, marginBottom: 16 }}>
        <SummaryCard label="New" value={s?.new ?? 0} tone="info" onClick={() => { setStatus("new"); setPage(1); }} active={status === "new"} />
        <SummaryCard label="Contacted" value={s?.contacted ?? 0} tone="warning" onClick={() => { setStatus("contacted"); setPage(1); }} active={status === "contacted"} />
        <SummaryCard label="Converted" value={s?.converted ?? 0} tone="success" onClick={() => { setStatus("converted"); setPage(1); }} active={status === "converted"} />
        <SummaryCard label="Closed" value={s?.closed ?? 0} onClick={() => { setStatus("closed"); setPage(1); }} active={status === "closed"} />
        <SummaryCard label="Total" value={s?.total ?? 0} onClick={() => { setStatus(undefined); setPage(1); }} active={!status} />
      </div>

      <DataTable
        loading={leads.loading}
        rows={(leads.data?.items ?? []) as unknown as Record<string, unknown>[]}
        emptyText="No leads for this filter."
        onRowClick={row => setSelected(row as unknown as GlobalServiceLead)}
        columns={[
          { key: "global_service_name", label: "Service" },
          { key: "name", label: "Customer" },
          { key: "phone", label: "Phone" },
          { key: "zipcode", label: "Zipcode", render: v => v ? String(v) : "—" },
          { key: "status", label: "Status", render: v => <Badge variant={STATUS_VARIANT[String(v)] ?? "muted"}>{String(v)}</Badge> },
          { key: "created_at", label: "Received", render: v => dt(v as string) },
        ]}
      />
      <Pagination page={page} total={leads.data?.total ?? 0} pageSize={20} onPage={setPage} />

      <Modal open={!!selected} onClose={() => setSelected(null)} title="Lead Detail" size="md">
        {selected && <LeadDetail lead={selected} onUpdated={() => { leads.refetch(); summary.refetch(); setSelected(null); }} />}
      </Modal>
    </div>
  );
}

function LeadDetail({ lead, onUpdated }: { lead: GlobalServiceLead; onUpdated: () => void }) {
  const [notes, setNotes] = useState(lead.admin_notes ?? "");
  const updateAction = useAction(useCallback((data: { status?: string; admin_notes?: string }) =>
    globalServicesApi.updateLead(lead.id, data), [lead.id]));

  async function setStatus(status: string) {
    const r = await updateAction.execute({ status });
    if (r) onUpdated();
  }
  async function saveNotes() {
    const r = await updateAction.execute({ admin_notes: notes });
    if (r) onUpdated();
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, fontSize: 13 }}>
        <div><strong>Service:</strong> {lead.global_service_name}</div>
        <div><strong>Status:</strong> <Badge variant={STATUS_VARIANT[lead.status] ?? "muted"}>{lead.status}</Badge></div>
        <div><strong>Name:</strong> {lead.name}</div>
        <div><strong>Phone:</strong> <a href={`tel:${lead.phone}`} style={{ color: "var(--brand)" }}>{lead.phone}</a></div>
        {lead.email && <div><strong>Email:</strong> {lead.email}</div>}
        {lead.zipcode && <div><strong>Zipcode:</strong> {lead.zipcode}</div>}
      </div>
      {lead.message && (
        <div style={{ padding: "8px 10px", borderRadius: 8, background: "var(--surface-sunken)", border: "1px solid var(--border)" }}>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: "0 0 4px" }}>Customer message</p>
          <p style={{ fontSize: 13, margin: 0 }}>{lead.message}</p>
        </div>
      )}
      <div>
        <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>Admin notes (call outcome, follow-up, etc.)</label>
        <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={3}
          style={{ width: "100%", padding: "8px 10px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)",
            background: "var(--bg)", color: "var(--text-primary)", fontSize: 13, boxSizing: "border-box", resize: "vertical" }} />
        <Btn variant="ghost" size="sm" onClick={saveNotes} disabled={updateAction.loading} style={{ marginTop: 6 }}>Save Notes</Btn>
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <Btn variant="secondary" size="sm" icon={<Phone size={12} />} disabled={updateAction.loading || lead.status === "contacted"}
          onClick={() => setStatus("contacted")}>Mark Contacted</Btn>
        <Btn variant="primary" size="sm" disabled={updateAction.loading || lead.status === "converted"}
          onClick={() => setStatus("converted")}>Mark Converted</Btn>
        <Btn variant="ghost" size="sm" disabled={updateAction.loading || lead.status === "closed"}
          onClick={() => setStatus("closed")}>Close Lead</Btn>
      </div>
      {updateAction.error && <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>{updateAction.error}</p>}
    </div>
  );
}
