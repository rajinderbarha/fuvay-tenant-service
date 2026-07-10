"use client";
import React, { useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, SectionHeader, Modal, Input } from "../../../../components/shared/ui";
import { serviceOptionApi, type ServiceOption34E, type ServiceOptionMapping34E } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import { ArrowLeft, Pencil, Power, PowerOff, Archive, ExternalLink } from "lucide-react";

const OPTION_TYPE_LABEL: Record<string, string> = {
  add_on: "Add-On", upgrade: "Upgrade", material: "Material", tool: "Tool",
  visit_fee: "Visit Fee", type: "Type/Variant", package: "Package", size: "Size",
  duration: "Duration", mode: "Mode", unit: "Unit", custom: "Custom",
};

const UNIT_LABEL: Record<string, string> = {
  per_unit: "/ unit", per_hour: "/ hr", flat: "flat", per_sqft: "/ sq.ft",
  per_kg: "/ kg", per_item: "/ item", per_visit: "/ visit", none: "—",
};

function InfoRow({ label, value }: { label: string; value?: string | number | null | React.ReactNode }) {
  return (
    <div style={{ display: "flex", gap: 12, padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
      <div style={{ width: 160, fontSize: 12, color: "var(--muted-text)", flexShrink: 0 }}>{label}</div>
      <div style={{ fontSize: 13, color: "var(--text)", fontWeight: 500 }}>{value ?? "—"}</div>
    </div>
  );
}

const EDIT_BLANK = {
  name: "", code: "", option_type: "add_on", unit: "per_unit",
  default_price: "0", description: "", is_customer_selectable: true, display_order: 0,
};
type FormState = typeof EDIT_BLANK;

export default function ServiceOptionDetailPage() {
  const params = useParams<{ id: string }>();
  const optionId = params?.id ?? "";

  const optionFetch = useApi(
    useCallback(() => serviceOptionApi.getOption(optionId), [optionId])
  );
  const option: ServiceOption34E | null =
    (optionFetch.data as { data?: ServiceOption34E } | null)?.data ??
    (optionFetch.data as ServiceOption34E | null);

  // Mappings — list of services this option is mapped to
  // We use the master-services/{svc}/options reverse endpoint is not perfect for this view,
  // so we use the option's own mapped_services_count and just show services via catalog API.
  // The detail view shows mapped services via the global list filtered by this option.
  const mappingsFetch = useApi(
    useCallback(
      () => serviceOptionApi.listOptions({ master_service_id: undefined, page_size: 1 }),
      // We'll use a separate fetch for service-level mappings if available
      // For now show the option mappings from the option detail
      []
    )
  );

  const [editModal, setEditModal] = useState(false);
  const [form, setForm] = useState<FormState>(EDIT_BLANK);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);

  const notify = (msg: string, ok = true) => {
    setToast({ msg, ok }); setTimeout(() => setToast(null), 3500);
  };

  function openEdit() {
    if (!option) return;
    setForm({
      name: option.name,
      code: option.code,
      option_type: option.option_type,
      unit: option.unit,
      default_price: option.default_price,
      description: option.description ?? "",
      is_customer_selectable: option.is_customer_selectable,
      display_order: option.display_order,
    });
    setEditModal(true);
  }

  const editAction = useAction(async (data: FormState) => {
    await serviceOptionApi.updateOption(optionId, {
      name: data.name,
      code: data.code,
      option_type: data.option_type,
      unit: data.unit,
      default_price: data.default_price,
      description: data.description || undefined,
      is_customer_selectable: data.is_customer_selectable,
      display_order: data.display_order,
    });
    optionFetch.refetch();
    setEditModal(false);
    notify("Option updated.");
  });

  const activateAction = useAction(async () => {
    await serviceOptionApi.activateOption(optionId);
    optionFetch.refetch();
    notify("Option activated.");
  });

  const deactivateAction = useAction(async () => {
    await serviceOptionApi.deactivateOption(optionId);
    optionFetch.refetch();
    notify("Option deactivated.");
  });

  const archiveAction = useAction(async () => {
    await serviceOptionApi.archiveOption(optionId);
    optionFetch.refetch();
    notify("Option archived.");
  });

  const statusVariant: Record<string, "success" | "warning" | "muted" | "danger"> = {
    active: "success", inactive: "warning", archived: "muted",
  };

  return (
    <AdminLayout activeNav="service-options">
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
        <Link href="/admin/service-options"
          style={{ color: "var(--muted-text)", display: "flex", alignItems: "center", gap: 4, fontSize: 13, textDecoration: "none" }}>
          <ArrowLeft size={15}/> Service Options
        </Link>
      </div>

      {toast && (
        <div style={{ padding: "10px 16px", borderRadius: 10, marginBottom: 12,
          background: toast.ok ? "var(--success-bg)" : "var(--danger-bg)",
          border: `1px solid ${toast.ok ? "var(--success-border)" : "var(--danger-border)"}`,
          color: toast.ok ? "var(--success-text)" : "var(--danger-text)", fontSize: 13 }}>
          {toast.ok ? "✓" : "✗"} {toast.msg}
        </div>
      )}

      <SectionHeader
        title={optionFetch.loading ? "Loading…" : (option?.name ?? "Service Option")}
        subtitle={option ? `Code: ${option.code} · ${OPTION_TYPE_LABEL[option.option_type] ?? option.option_type}` : ""}
      />

      {optionFetch.error ? (
        <Card padding={32} style={{ textAlign: "center" }}>
          <p style={{ color: "var(--danger-text,#b91c1c)", fontSize: 14 }}>
            Could not load option. {optionFetch.error}
          </p>
          <Btn variant="secondary" size="sm" onClick={() => optionFetch.refetch()} style={{ marginTop: 12 }}>
            Retry
          </Btn>
        </Card>
      ) : optionFetch.loading ? (
        <Card padding={32}><div style={{ color: "var(--muted-text)", fontSize: 13 }}>Loading…</div></Card>
      ) : option ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Action bar */}
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <Btn variant="secondary" size="sm" onClick={openEdit}><Pencil size={13}/> Edit</Btn>
            {option.status === "active" ? (
              <Btn variant="secondary" size="sm" loading={deactivateAction.loading}
                onClick={() => deactivateAction.execute()}>
                <PowerOff size={13}/> Deactivate
              </Btn>
            ) : option.status === "inactive" ? (
              <Btn variant="primary" size="sm" loading={activateAction.loading}
                onClick={() => activateAction.execute()}>
                <Power size={13}/> Activate
              </Btn>
            ) : null}
            {option.status !== "archived" && (
              <Btn variant="ghost" size="sm" loading={archiveAction.loading}
                onClick={() => archiveAction.execute()}
                style={{ color: "var(--danger-text,#b91c1c)" }}>
                <Archive size={13}/> Archive
              </Btn>
            )}
          </div>

          {/* Stats row */}
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {[
              { label: "Status",   value: <Badge variant={statusVariant[option.status] ?? "muted"}>{option.status}</Badge> },
              { label: "Type",     value: <Badge variant="info" size="sm">{OPTION_TYPE_LABEL[option.option_type] ?? option.option_type}</Badge> },
              { label: "Unit",     value: UNIT_LABEL[option.unit] ?? option.unit },
              { label: "Price",    value: `₹${Number(option.default_price).toFixed(2)}` },
              { label: "Customer Selectable", value: option.is_customer_selectable ? "Yes" : "No" },
              { label: "Display Order", value: option.display_order },
            ].map(({ label, value }) => (
              <div key={label} style={{
                background: "var(--card-bg)", border: "1px solid var(--border)", borderRadius: 8,
                padding: "12px 16px", flex: 1, minWidth: 100,
              }}>
                <div style={{ fontSize: 11, color: "var(--muted-text)", marginBottom: 4 }}>{label}</div>
                <div style={{ fontSize: 14, fontWeight: 700 }}>{value}</div>
              </div>
            ))}
          </div>

          {/* Details card */}
          <Card padding={20}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "var(--muted-text)", textTransform: "uppercase",
              letterSpacing: "0.05em", marginBottom: 12 }}>Option Details</div>
            <InfoRow label="ID"          value={<span style={{ fontFamily: "monospace", fontSize: 12 }}>{option.id}</span>}/>
            <InfoRow label="Name"        value={option.name}/>
            <InfoRow label="Code"        value={<span style={{ fontFamily: "monospace" }}>{option.code}</span>}/>
            <InfoRow label="Slug"        value={<span style={{ fontFamily: "monospace", fontSize: 12 }}>{option.slug}</span>}/>
            <InfoRow label="Description" value={option.description}/>
            <InfoRow label="Option Type" value={OPTION_TYPE_LABEL[option.option_type] ?? option.option_type}/>
            <InfoRow label="Unit"        value={`${option.unit} (${UNIT_LABEL[option.unit] ?? option.unit})`}/>
            <InfoRow label="Default Price" value={`₹${Number(option.default_price).toFixed(2)}`}/>
            {option.min_price && <InfoRow label="Min Price" value={`₹${Number(option.min_price).toFixed(2)}`}/>}
            {option.max_price && <InfoRow label="Max Price" value={`₹${Number(option.max_price).toFixed(2)}`}/>}
            <InfoRow label="Customer Selectable" value={option.is_customer_selectable ? "Yes" : "No"}/>
            <InfoRow label="Status"      value={option.status}/>
            <InfoRow label="Vertical"    value={option.vertical_type}/>
            <InfoRow label="Created"     value={option.created_at ? new Date(option.created_at).toLocaleString("en-IN") : undefined}/>
            <InfoRow label="Updated"     value={option.updated_at ? new Date(option.updated_at).toLocaleString("en-IN") : undefined}/>
          </Card>

          {/* Service mappings note */}
          <Card padding={20}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "var(--muted-text)", textTransform: "uppercase",
              letterSpacing: "0.05em", marginBottom: 12 }}>Service Mappings</div>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 12px" }}>
              To view or manage which services this option is mapped to, go to{" "}
              <Link href="/admin/catalog" style={{ color: "var(--primary)" }}>
                Master Services <ExternalLink size={11} style={{ verticalAlign: "middle" }}/>
              </Link>{" "}
              and open a service to manage its options.
            </p>
            <Link href={`/admin/service-options?mapped=false`}
              style={{ fontSize: 12, color: "var(--muted-text)", textDecoration: "none" }}>
              View all unmapped options →
            </Link>
          </Card>
        </div>
      ) : null}

      {/* Edit Modal */}
      <Modal open={editModal} onClose={() => setEditModal(false)} title="Edit Service Option">
        <div style={{ display: "flex", flexDirection: "column", gap: 14, maxHeight: "75vh", overflowY: "auto", paddingRight: 4 }}>
          {editAction.error && (
            <div style={{ padding: "10px 14px", borderRadius: 9, background: "var(--danger-bg)",
              border: "1px solid var(--danger-border)" }}>
              <p style={{ fontSize: 12, color: "var(--danger-text)", margin: 0 }}>{editAction.error}</p>
            </div>
          )}
          <Input label="Name *" placeholder="Wall Mounting" value={form.name}
            onChange={v => setForm(f => ({ ...f, name: v }))}/>
          <Input label="Code *" placeholder="WALL_MOUNT" value={form.code}
            onChange={v => setForm(f => ({ ...f, code: v.toUpperCase() }))}/>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Option Type *</label>
              <select value={form.option_type} onChange={e => setForm(f => ({ ...f, option_type: e.target.value }))}
                style={{ width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)",
                  background: "var(--bg)", color: "var(--text-primary)", fontSize: 13, outline: "none" }}>
                {Object.entries(OPTION_TYPE_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Unit *</label>
              <select value={form.unit} onChange={e => setForm(f => ({ ...f, unit: e.target.value }))}
                style={{ width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)",
                  background: "var(--bg)", color: "var(--text-primary)", fontSize: 13, outline: "none" }}>
                {["per_unit","per_hour","flat","per_sqft","per_kg","per_item","per_visit","none"].map(u => (
                  <option key={u} value={u}>{UNIT_LABEL[u] ?? u}</option>
                ))}
              </select>
            </div>
          </div>
          <Input label="Default Price (₹)" type="number" placeholder="0" value={form.default_price}
            onChange={v => setForm(f => ({ ...f, default_price: v }))}/>
          <div>
            <label style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>Description</label>
            <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              placeholder="Brief description…" rows={2}
              style={{ width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)",
                background: "var(--bg)", color: "var(--text-primary)", fontSize: 13, fontFamily: "inherit",
                resize: "vertical", outline: "none", boxSizing: "border-box" }}/>
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
            <input type="checkbox" checked={form.is_customer_selectable}
              onChange={e => setForm(f => ({ ...f, is_customer_selectable: e.target.checked }))}/>
            <span style={{ fontSize: 13, color: "var(--text-primary)" }}>Customer can select this option</span>
          </label>
          <Input label="Display Order" type="number" value={String(form.display_order)}
            onChange={v => setForm(f => ({ ...f, display_order: Number(v) || 0 }))}/>
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setEditModal(false)}>Cancel</Btn>
            <Btn variant="primary" size="sm"
              disabled={!form.name.trim() || !form.code.trim()}
              loading={editAction.loading}
              onClick={() => editAction.execute(form)}>
              Save Changes
            </Btn>
          </div>
        </div>
      </Modal>
    </AdminLayout>
  );
}
