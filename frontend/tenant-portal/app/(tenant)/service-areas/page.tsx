"use client";
import React, { useCallback, useState } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { Card, Badge, Btn, Modal, Input, Skeleton } from "../../../components/shared/ui";
import { serviceAreaApi } from "../../../lib/api";
import type { GeoZone, GeoZoneCreatePayload } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { MapPin } from "lucide-react";

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
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:24 }}>
        <div>
          <h1 style={{ fontSize:22, fontWeight:700, color:"var(--text-primary)", margin:"0 0 4px" }}>
            Service Areas
          </h1>
          <p style={{ fontSize:13, color:"var(--text-secondary)", margin:0 }}>
            Configure which cities, pincodes, or zones your business covers.
          </p>
        </div>
        <Btn variant="primary" size="sm" onClick={() => setCreateModal(true)}>+ Add Zone</Btn>
      </div>

      {toast && (
        <div style={{ padding:"10px 16px", background:"var(--success-bg)", border:"1px solid var(--success-border)",
          borderRadius:10, color:"var(--success-text)", fontSize:13, marginBottom:16 }}>
          ✓ {toast}
        </div>
      )}

      {!areas.loading && list.length === 0 && (
        <div style={{ padding:"12px 16px", borderRadius:10, background:"var(--warning-bg)",
          border:"1px solid var(--warning-border)", marginBottom:16 }}>
          <p style={{ fontSize:13, color:"var(--warning-text)", margin:0 }}>
            ⚠ No service zones configured — customers won&apos;t be matched to your business until you add at least one.
          </p>
        </div>
      )}

      {areas.loading ? (
        <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
          {[...Array(4)].map((_, i) => <Skeleton key={i} height={64} style={{ borderRadius:10 }}/>)}
        </div>
      ) : list.length === 0 ? (
        <Card padding={48} style={{ textAlign:"center" }}>
          <MapPin size={32} style={{ color:"var(--text-tertiary)", margin:"0 auto 12px" }}/>
          <p style={{ fontSize:14, color:"var(--text-secondary)", margin:0 }}>No service zones yet</p>
        </Card>
      ) : (
        <Card padding={0}>
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
                    <Badge variant="muted">{zone.zone_type}</Badge>
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
                    <Badge variant={zone.is_active ? "success" : "muted"}>{zone.is_active ? "Active" : "Inactive"}</Badge>
                  </td>
                  <td style={{ padding:"12px 16px" }}>
                    {zone.is_active && (
                      <Btn variant="ghost" size="xs" loading={deactivateAction.loading}
                        onClick={() => deactivateAction.execute(zone.zone_id)}>
                        Deactivate
                      </Btn>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      <Modal open={createModal} onClose={() => setCreateModal(false)} title="Add Service Zone">
        <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
          {createAction.error && (
            <div style={{ padding:"10px 14px", borderRadius:9, background:"var(--danger-bg)",
              border:"1px solid var(--danger-border)" }}>
              <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>{createAction.error}</p>
            </div>
          )}
          <Input label="Zone Name" placeholder="Mumbai North, Delhi NCR…"
            value={form.zone_name} onChange={v => setForm(f => ({ ...f, zone_name: v }))}/>
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
                onChange={v => setForm(f => ({ ...f, center_lat: Number(v) || undefined }))}/>
              <Input label="Center Longitude" type="number" placeholder="75.8"
                value={form.center_lng != null ? String(form.center_lng) : ""}
                onChange={v => setForm(f => ({ ...f, center_lng: Number(v) || undefined }))}/>
              <Input label="Radius (km)" type="number" placeholder="10"
                value={form.radius_km != null ? String(form.radius_km) : ""}
                onChange={v => setForm(f => ({ ...f, radius_km: Number(v) || undefined }))}/>
            </>
          )}
          <Input label="Surcharge %" type="number" placeholder="0"
            value={form.surcharge_pct != null ? String(form.surcharge_pct) : "0"}
            onChange={v => setForm(f => ({ ...f, surcharge_pct: Number(v) || 0 }))}/>
          <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setCreateModal(false)}>Cancel</Btn>
            <Btn variant="primary" size="sm" loading={createAction.loading}
              disabled={!form.zone_name.trim()}
              onClick={handleSubmit}>
              Add Zone
            </Btn>
          </div>
        </div>
      </Modal>
    </TenantLayout>
  );
}
