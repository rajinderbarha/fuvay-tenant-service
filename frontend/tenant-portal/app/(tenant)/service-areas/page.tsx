"use client";
import React, { useCallback, useState } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import {
  PageHeader, Card, Button, Modal, Input, Skeleton,
  StatusBadge as DsStatusBadge, Alert, EmptyState,
} from "@serviceos/design-system";
import { serviceAreaApi } from "../../../lib/api";
import type { GeoZone, GeoZoneCreatePayload } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";

const ZONE_TYPE_OPTIONS = [
  { value: "pincode", label: "Pincodes" },
  { value: "city",    label: "City" },
  { value: "radius",  label: "Radius (km)" },
];

const BLANK: GeoZoneCreatePayload = {
  zone_name: "", zone_type: "pincode", identifiers: [], radius_km: undefined,
};

export default function ServiceAreasPage() {
  const areas = useApi(useCallback(() => serviceAreaApi.list(), []));
  const [createModal, setCreateModal] = useState(false);
  const [form, setForm] = useState<GeoZoneCreatePayload>(BLANK);
  const [identsText, setIdentsText] = useState("");
  const [toast, setToast] = useState("");

  const createAction = useAction(async (payload: GeoZoneCreatePayload) => {
    await serviceAreaApi.create(payload);
    areas.refetch();
    setCreateModal(false);
    setForm(BLANK);
    setIdentsText("");
    notify("Service zone added.");
  });

  const deactivateAction = useAction(async (zoneId: string) => {
    await serviceAreaApi.deactivate(zoneId);
    areas.refetch();
    notify("Zone deactivated.");
  });

  const notify = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 3500); };

  const list: GeoZone[] = areas.data?.zones ?? [];

  function handleSubmit() {
    const idents = identsText.split(/[\s,]+/).map(s => s.trim()).filter(Boolean);
    createAction.execute({ ...form, identifiers: idents });
  }

  return (
    <TenantLayout activeNav="service-areas">
      <div style={{ marginBottom: 24 }}>
        <PageHeader
          title="Service Areas"
          description="Configure which cities, pincodes, or zones your business covers."
          actions={<Button variant="primary" size="sm" onClick={() => setCreateModal(true)}>+ Add Zone</Button>}
        />
      </div>

      {toast && (
        <div style={{ marginBottom: 16 }}>
          <Alert tone="success">{toast}</Alert>
        </div>
      )}

      {!areas.loading && list.length === 0 && (
        <div style={{ marginBottom: 16 }}>
          <Alert tone="warning">
            No service zones configured — customers won&apos;t be matched to your business until you add at least one.
          </Alert>
        </div>
      )}

      {areas.loading ? (
        <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
          {[...Array(4)].map((_, i) => <Skeleton key={i} height="4rem" radius="10px"/>)}
        </div>
      ) : list.length === 0 ? (
        <Card padding="lg">
          <EmptyState
            title="No service zones yet"
            description="Add a zone to start matching customers to your business."
          />
        </Card>
      ) : (
        <Card padding="none">
          <div style={{ overflowX: "auto" }}>
            <table style={{ width:"100%", borderCollapse:"collapse" }}>
              <thead>
                <tr style={{ background:"var(--surface-sunken)", borderBottom:"1px solid var(--border)" }}>
                  {["Zone Name","Type","Coverage","Surcharge","Status","Actions"].map(h => (
                    <th key={h} style={{ padding:"10px 16px", textAlign:"left", fontSize:11, fontWeight:700,
                      color:"var(--text-tertiary)", textTransform:"uppercase", letterSpacing:"0.06em" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {list.map((zone, i) => (
                  <tr key={zone.zone_id} style={{ borderBottom: i < list.length-1 ? "1px solid var(--border)" : "none" }}>
                    <td style={{ padding:"12px 16px", fontWeight:600, fontSize:13, color:"var(--text-primary)" }}>
                      {zone.zone_name}
                    </td>
                    <td style={{ padding:"12px 16px" }}>
                      <DsStatusBadge status={zone.zone_type}/>
                    </td>
                    <td style={{ padding:"12px 16px", fontSize:12, color:"var(--text-secondary)" }}>
                      {zone.zone_type === "radius" && zone.radius_km
                        ? `${zone.radius_km} km radius`
                        : zone.identifiers.length > 0
                          ? `${zone.identifiers.slice(0,4).join(", ")}${zone.identifiers.length > 4 ? ` +${zone.identifiers.length-4}` : ""}`
                          : "—"}
                    </td>
                    <td style={{ padding:"12px 16px", fontSize:13, color:"var(--text-secondary)" }}>
                      {zone.surcharge_pct > 0 ? `+${zone.surcharge_pct}%` : "None"}
                    </td>
                    <td style={{ padding:"12px 16px" }}>
                      <DsStatusBadge status={zone.is_active ? "active" : "inactive"}/>
                    </td>
                    <td style={{ padding:"12px 16px" }}>
                      {zone.is_active && (
                        <Button variant="ghost" size="sm" loading={deactivateAction.loading}
                          onClick={() => deactivateAction.execute(zone.zone_id)}>
                          Deactivate
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <Modal
        open={createModal}
        onClose={() => setCreateModal(false)}
        title="Add Service Zone"
        footer={<>
          <Button variant="ghost" size="sm" onClick={() => setCreateModal(false)}>Cancel</Button>
          <Button variant="primary" size="sm" loading={createAction.loading}
            disabled={!form.zone_name.trim()}
            onClick={handleSubmit}>
            Add Zone
          </Button>
        </>}
      >
        <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
          {createAction.error && (
            <Alert tone="danger">{createAction.error}</Alert>
          )}
          <Input label="Zone Name" placeholder="Mumbai North, Delhi NCR…"
            value={form.zone_name} onChange={e => setForm(f => ({ ...f, zone_name: e.target.value }))}/>
          <div>
            <label style={{ fontSize:12, fontWeight:500, color:"var(--text-secondary)", display:"block", marginBottom:6 }}>
              Zone Type
            </label>
            <div style={{ display:"flex", gap:8 }}>
              {ZONE_TYPE_OPTIONS.map(opt => (
                <button key={opt.value} onClick={() => setForm(f => ({ ...f, zone_type: opt.value }))}
                  style={{ flex:1, padding:"8px 4px", borderRadius:8, border:"1px solid",
                    borderColor: form.zone_type===opt.value ? "var(--accent)" : "var(--border)",
                    background: form.zone_type===opt.value ? "var(--accent-subtle)" : "var(--surface)",
                    color: form.zone_type===opt.value ? "var(--accent)" : "var(--text-secondary)",
                    fontWeight:600, fontSize:11, cursor:"pointer" }}>
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
          {(form.zone_type === "pincode" || form.zone_type === "city") && (
            <div>
              <label style={{ fontSize:12, fontWeight:500, color:"var(--text-secondary)", display:"block", marginBottom:6 }}>
                {form.zone_type === "pincode" ? "Pincodes (comma or space separated)" : "Cities (comma separated)"}
              </label>
              <textarea
                value={identsText}
                onChange={e => setIdentsText(e.target.value)}
                placeholder={form.zone_type === "pincode" ? "141001, 141002, 141003" : "Ludhiana, Amritsar"}
                rows={3}
                style={{ width:"100%", padding:"8px 10px", borderRadius:8, border:"1px solid var(--border)",
                  background:"var(--bg)", color:"var(--text-primary)", fontSize:13, fontFamily:"inherit",
                  resize:"vertical", outline:"none", boxSizing:"border-box" }}
              />
            </div>
          )}
          {form.zone_type === "radius" && (
            <>
              <Input label="Center Latitude" type="number" placeholder="30.9"
                value={form.center_lat != null ? String(form.center_lat) : ""}
                onChange={e => setForm(f => ({ ...f, center_lat: Number(e.target.value) || undefined }))}/>
              <Input label="Center Longitude" type="number" placeholder="75.8"
                value={form.center_lng != null ? String(form.center_lng) : ""}
                onChange={e => setForm(f => ({ ...f, center_lng: Number(e.target.value) || undefined }))}/>
              <Input label="Radius (km)" type="number" placeholder="10"
                value={form.radius_km != null ? String(form.radius_km) : ""}
                onChange={e => setForm(f => ({ ...f, radius_km: Number(e.target.value) || undefined }))}/>
            </>
          )}
          <Input label="Surcharge %" type="number" placeholder="0"
            value={form.surcharge_pct != null ? String(form.surcharge_pct) : "0"}
            onChange={e => setForm(f => ({ ...f, surcharge_pct: Number(e.target.value) || 0 }))}/>
        </div>
      </Modal>
    </TenantLayout>
  );
}
