"use client";
/**
 * Service Catalog — tenant-owned definitions that drive job_type selection,
 * checklist auto-population, and pricing model for every booking and direct job.
 *
 * REPAIR      → assessment + quote required before work starts
 * SERVICE     → fixed price, checklist required, no quote
 * CONSULTATION → assessment + report + optional repair spawn
 */
import React, { useCallback, useState } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { Card, Badge, Btn, Modal, Input, Skeleton } from "../../../components/shared/ui";
import { catalogApi, masterCatalogApi } from "../../../lib/api";
import type { ServiceCatalogItem, AdminMasterServiceRow } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { ChecklistSelectionPanel } from "../../../components/checklist/ChecklistSelectionPanel";

const TYPE_LABEL: Record<string, string>  = { repair:"Repair", service:"Service", consultation:"Consultation" };
const TYPE_COLOR: Record<string, string>  = { repair:"warning", service:"success", consultation:"info" };
const PRICE_LABEL: Record<string, string> = { fixed:"Fixed price", post_assessment:"Post-assessment", hourly:"Hourly" };

const BLANK: Partial<ServiceCatalogItem> = {
  service_type_id:"", name:"", category:"", description:"",
  service_type:"service", pricing_model:"fixed",
  base_price:undefined, estimated_duration_minutes:undefined,
  checklist_required:false, checklist_template:[],
};

export default function CatalogPage() {
  const [pageTab, setPageTab] = useState<"admin" | "custom" | "checklists">("admin");
  return (
    <TenantLayout activeNav="catalog">
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:16 }}>
        <div>
          <h1 style={{ fontSize:22, fontWeight:700, color:"var(--text-primary)", margin:"0 0 4px" }}>
            Service Catalog
          </h1>
          <p style={{ fontSize:13, color:"var(--text-secondary)", margin:0 }}>
            Enable services from the admin master catalog, or define a custom service of your own.
          </p>
        </div>
      </div>
      <div style={{ display:"flex", gap:2, borderBottom:"2px solid var(--border)", marginBottom:20 }}>
        {([["admin","Admin Catalog"],["custom","Custom Services"],["checklists","Checklists"]] as const).map(([id,label]) => (
          <button key={id} onClick={() => setPageTab(id)}
            style={{ padding:"10px 16px", border:"none", background:"none", cursor:"pointer",
              fontSize:13, fontWeight:pageTab===id?700:500,
              color: pageTab===id ? "var(--accent)" : "var(--text-secondary)",
              borderBottom: pageTab===id ? "2px solid var(--accent)" : "2px solid transparent",
              marginBottom:-2 }}>
            {label}
          </button>
        ))}
      </div>
      {pageTab === "admin" ? <AdminCatalogSection/>
        : pageTab === "custom" ? <CustomCatalogSection/>
        : <ChecklistsSection/>}
    </TenantLayout>
  );
}

function AdminCatalogSection() {
  const available = useApi(useCallback(() => masterCatalogApi.listAvailable(), []));
  const enableAction = useAction(useCallback(
    (data: { master_service_id:string; job_type_id:string }) => masterCatalogApi.enable(data), []));
  const disableAction = useAction(useCallback(
    (masterServiceId: string, jobTypeId: string) => masterCatalogApi.disable(masterServiceId, jobTypeId), []));

  async function handleToggle(svc: AdminMasterServiceRow) {
    if (!svc.job_type_id) return;
    const res = svc.is_enabled
      ? await disableAction.execute(svc.service_id, svc.job_type_id)
      : await enableAction.execute({ master_service_id: svc.service_id, job_type_id: svc.job_type_id });
    if (res !== null) available.refetch();
  }

  const services = available.data?.services ?? [];
  const TYPE_COLOR: Record<string, "warning"|"success"|"info"> = { repair:"warning", service:"success", consultation:"info" };

  return (
    <div>
      {available.error && (
        <div style={{ padding:"12px 16px", borderRadius:10, background:"var(--danger-bg)",
          border:"1px solid var(--danger-border)", marginBottom:16 }}>
          <p style={{ fontSize:13, color:"var(--danger-text)", margin:0 }}>{available.error}</p>
        </div>
      )}
      {available.loading ? (
        <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
          {[...Array(4)].map((_,i) => <Skeleton key={i} height={80} style={{ borderRadius:"var(--radius-lg)" }}/>)}
        </div>
      ) : services.length === 0 ? (
        <Card padding={48} style={{ textAlign:"center" }}>
          <p style={{ fontSize:13, color:"var(--text-secondary)", margin:0 }}>
            No services published by the admin catalog yet. Check back later, or use Custom Services.
          </p>
        </Card>
      ) : (
        <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(320px, 1fr))", gap:12 }}>
          {services.map(svc => (
            <Card key={svc.offering_key ?? `${svc.service_id}:${svc.job_type_id}`} padding={18}>
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:8 }}>
                <div>
                  <p style={{ fontSize:14, fontWeight:600, color:"var(--text-primary)", margin:"0 0 2px" }}>{svc.service_name}</p>
                  <Badge variant={TYPE_COLOR[svc.job_type] ?? "muted"}>{svc.job_type_label || svc.job_type}</Badge>
                </div>
                <Badge variant={svc.is_enabled ? "success" : "muted"}>{svc.is_enabled ? "Enabled" : "Not enabled"}</Badge>
              </div>
              {svc.description && <p style={{ fontSize:12, color:"var(--text-secondary)", margin:"0 0 10px" }}>{svc.description}</p>}
              <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"0 0 10px" }}>
                Admin base price ₹{svc.base_price.toLocaleString("en-IN")}
                {svc.visit_fee > 0 && ` · ₹${svc.visit_fee} visit fee`}
              </p>
              <Btn variant={svc.is_enabled ? "ghost" : "primary"} size="sm"
                loading={enableAction.loading || disableAction.loading} onClick={() => handleToggle(svc)}>
                {svc.is_enabled ? "Disable" : "Enable for my business"}
              </Btn>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function CustomCatalogSection() {
  const catalog = useApi(useCallback(() => catalogApi.list(), []));

  const createAction     = useAction((data: Partial<ServiceCatalogItem>) => catalogApi.create(data));
  const deactivateAction = useAction((id: string) => catalogApi.deactivate(id));

  const [createModal, setCreateModal] = useState(false);
  const [form,        setForm]        = useState<Partial<ServiceCatalogItem>>(BLANK);
  const [checklistInput, setChecklistInput] = useState(""); // newline-separated steps

  function set<K extends keyof ServiceCatalogItem>(k: K, v: ServiceCatalogItem[K]) {
    setForm(f => ({ ...f, [k]: v }));
  }

  async function handleCreate() {
    const steps = checklistInput.split("\n").map(s => s.trim()).filter(Boolean);
    const payload: Partial<ServiceCatalogItem> = {
      ...form,
      checklist_required: steps.length > 0 || form.checklist_required,
      checklist_template: steps.length > 0 ? steps : undefined,
    };
    const res = await createAction.execute(payload);
    if (res) {
      catalog.refetch();
      setCreateModal(false);
      setForm(BLANK);
      setChecklistInput("");
    }
  }

  async function handleDeactivate(id: string) {
    const res = await deactivateAction.execute(id);
    if (res !== null) catalog.refetch();
  }

  const items: ServiceCatalogItem[] = catalog.data?.items ?? [];
  const byType = {
    repair:       items.filter(i => i.service_type === "repair"),
    service:      items.filter(i => i.service_type === "service"),
    consultation: items.filter(i => i.service_type === "consultation"),
  };

  return (
    <div>
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:16 }}>
        <p style={{ fontSize:12, color:"var(--text-tertiary)", margin:0 }}>
          Services you define yourself — not vetted by the admin master catalog.
        </p>
        <Btn variant="primary" size="sm" onClick={() => setCreateModal(true)}>
          + Add Custom Service
        </Btn>
      </div>

      {catalog.loading ? (
        <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
          {[...Array(4)].map((_,i) => <Skeleton key={i} height={80} style={{ borderRadius:"var(--radius-lg)" }}/>)}
        </div>
      ) : items.length === 0 ? (
        <Card padding={48} style={{ textAlign:"center" }}>
          <p style={{ fontSize:32, margin:"0 0 12px" }}>📋</p>
          <h2 style={{ fontSize:18, fontWeight:600, color:"var(--text-primary)", margin:"0 0 8px" }}>
            No services defined yet
          </h2>
          <p style={{ fontSize:13, color:"var(--text-secondary)", margin:"0 0 20px" }}>
            Add your first service to enable job_type routing, auto-checklists, and catalog-based pricing.
          </p>
          <Btn variant="primary" onClick={() => setCreateModal(true)}>Add First Service</Btn>
        </Card>
      ) : (
        <div style={{ display:"flex", flexDirection:"column", gap:20 }}>
          {(["repair", "service", "consultation"] as const).map(type => (
            byType[type].length > 0 && (
              <div key={type}>
                <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:10 }}>
                  <Badge variant={TYPE_COLOR[type] as "warning"|"success"|"info"}>{TYPE_LABEL[type]}</Badge>
                  <span style={{ fontSize:12, color:"var(--text-tertiary)" }}>{byType[type].length} service{byType[type].length>1?"s":""}</span>
                </div>
                <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(320px, 1fr))", gap:12 }}>
                  {byType[type].map(item => (
                    <Card key={item.id} padding={18} style={{ opacity: item.is_active ? 1 : 0.5 }}>
                      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:8 }}>
                        <div>
                          <p style={{ fontSize:14, fontWeight:600, color:"var(--text-primary)", margin:"0 0 2px" }}>
                            {item.name}
                          </p>
                          <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:0 }}>
                            {item.service_type_id}
                          </p>
                        </div>
                        <Badge variant={item.is_active ? "success" : "muted"}>
                          {item.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </div>

                      {item.description && (
                        <p style={{ fontSize:12, color:"var(--text-secondary)", margin:"0 0 10px" }}>
                          {item.description}
                        </p>
                      )}

                      <div style={{ display:"flex", gap:12, flexWrap:"wrap", marginBottom:10 }}>
                        <span style={{ fontSize:11, color:"var(--text-secondary)" }}>
                          {PRICE_LABEL[item.pricing_model] ?? item.pricing_model}
                          {item.base_price != null && ` · ₹${item.base_price.toLocaleString("en-IN")}`}
                        </span>
                        {item.estimated_duration_minutes != null && (
                          <span style={{ fontSize:11, color:"var(--text-secondary)" }}>
                            {item.estimated_duration_minutes} min
                          </span>
                        )}
                        {item.checklist_required && (
                          <span style={{ fontSize:11, color:"var(--info-text)" }}>
                            ✓ {item.checklist_template?.length ?? 0} checklist steps
                          </span>
                        )}
                      </div>

                      {item.is_active && (
                        <Btn variant="ghost" size="sm"
                          onClick={() => handleDeactivate(item.id)}>
                          Deactivate
                        </Btn>
                      )}
                    </Card>
                  ))}
                </div>
              </div>
            )
          ))}
        </div>
      )}

      {/* Create service modal */}
      <Modal open={createModal} onClose={() => setCreateModal(false)} title="Add Service to Catalog">
        <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
          {createAction.error && (
            <div style={{ padding:"10px 14px", borderRadius:9, background:"var(--danger-bg)",
              border:"1px solid var(--danger-border)" }}>
              <p style={{ fontSize:12, color:"var(--danger-text)", margin:0 }}>{createAction.error}</p>
            </div>
          )}

          <Input label="Service ID (unique, e.g. ac_cleaning)" placeholder="ac_cleaning"
            value={form.service_type_id ?? ""} onChange={v => set("service_type_id", v)}/>
          <Input label="Name" placeholder="AC Deep Cleaning"
            value={form.name ?? ""} onChange={v => set("name", v)}/>
          <Input label="Category (optional)" placeholder="HVAC"
            value={form.category ?? ""} onChange={v => set("category", v)}/>
          <Input label="Description (optional)" placeholder="Full cleaning of filters, coils, and drain..."
            value={form.description ?? ""} onChange={v => set("description", v)} rows={2}/>

          <div>
            <label style={{ fontSize:12, fontWeight:500, color:"var(--text-secondary)", display:"block", marginBottom:6 }}>
              Job Type — determines the workflow
            </label>
            <div style={{ display:"flex", gap:8 }}>
              {(["service","repair","consultation"] as const).map(t => (
                <button key={t} onClick={() => set("service_type", t)}
                  style={{ flex:1, padding:"8px 0", borderRadius:"var(--radius-md)", border:"1px solid",
                    borderColor: form.service_type===t ? "var(--accent)" : "var(--border)",
                    background: form.service_type===t ? "var(--accent-subtle)" : "var(--surface)",
                    color: form.service_type===t ? "var(--accent)" : "var(--text-secondary)",
                    fontWeight:600, fontSize:12, cursor:"pointer" }}>
                  {TYPE_LABEL[t]}
                </button>
              ))}
            </div>
            <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"6px 0 0" }}>
              {form.service_type === "service"      && "Fixed price. Checklist required. No assessment or quote."}
              {form.service_type === "repair"       && "Assessment → diagnosis → quote → work → quality check."}
              {form.service_type === "consultation" && "Assessment + report. Quote optional. Can spawn a repair job."}
            </p>
          </div>

          <div>
            <label style={{ fontSize:12, fontWeight:500, color:"var(--text-secondary)", display:"block", marginBottom:6 }}>
              Pricing Model
            </label>
            <div style={{ display:"flex", gap:8 }}>
              {(["fixed","post_assessment","hourly"] as const).map(m => (
                <button key={m} onClick={() => set("pricing_model", m)}
                  style={{ flex:1, padding:"8px 0", borderRadius:"var(--radius-md)", border:"1px solid",
                    borderColor: form.pricing_model===m ? "var(--accent)" : "var(--border)",
                    background: form.pricing_model===m ? "var(--accent-subtle)" : "var(--surface)",
                    color: form.pricing_model===m ? "var(--accent)" : "var(--text-secondary)",
                    fontWeight:600, fontSize:12, cursor:"pointer" }}>
                  {PRICE_LABEL[m]}
                </button>
              ))}
            </div>
          </div>

          {form.pricing_model === "fixed" && (
            <Input label="Base Price (₹)" type="number" placeholder="499"
              value={form.base_price != null ? String(form.base_price) : ""}
              onChange={v => set("base_price", Number(v))}/>
          )}

          <Input label="Estimated Duration (minutes)" type="number" placeholder="60"
            value={form.estimated_duration_minutes != null ? String(form.estimated_duration_minutes) : ""}
            onChange={v => set("estimated_duration_minutes", Number(v) || undefined)}/>

          <div>
            <label style={{ fontSize:12, fontWeight:500, color:"var(--text-secondary)", display:"block", marginBottom:6 }}>
              Checklist Steps (one per line, optional)
            </label>
            <textarea
              placeholder={"Inspect filters\nClean coils\nCheck refrigerant level"}
              value={checklistInput}
              onChange={e => setChecklistInput(e.target.value)}
              rows={4}
              style={{ width:"100%", borderRadius:"var(--radius-md)", border:"1px solid var(--border)",
                background:"var(--surface-sunken)", color:"var(--text-primary)",
                padding:"10px 12px", fontSize:12, fontFamily:"inherit",
                resize:"vertical", outline:"none", boxSizing:"border-box" }}
            />
            <p style={{ fontSize:11, color:"var(--text-tertiary)", margin:"4px 0 0" }}>
              {checklistInput.split("\n").filter(s => s.trim()).length} steps defined
            </p>
          </div>

          <div style={{ display:"flex", gap:10, justifyContent:"flex-end" }}>
            <Btn variant="ghost" size="sm" onClick={() => setCreateModal(false)}>Cancel</Btn>
            <Btn variant="primary" size="sm" loading={createAction.loading}
              disabled={!form.service_type_id?.trim() || !form.name?.trim()}
              onClick={handleCreate}>
              Add to Catalog
            </Btn>
          </div>
        </div>
      </Modal>
    </div>
  );
}

/**
 * Checklist selection, per enabled service.
 *
 * Scoped to ENABLED services only: a provider choosing checklist points for a
 * service they do not offer would be configuring nothing, and the backend's
 * selectable list is driven by that service's job types either way.
 */
function ChecklistsSection() {
  const enabled = useApi(useCallback(() => masterCatalogApi.listEnabled(), []));
  const [openServiceId, setOpenServiceId] = useState<string | null>(null);

  if (enabled.loading) return <Card><Skeleton/><Skeleton/></Card>;
  if (enabled.error) {
    return (
      <Card>
        <p style={{ fontSize:13, color:"var(--danger)", margin:0 }}>{enabled.error}</p>
        <div style={{ marginTop:12 }}><Btn variant="secondary" onClick={enabled.refetch}>Try again</Btn></div>
      </Card>
    );
  }

  const services = (enabled.data?.services ?? []).filter(s => s.is_enabled);
  if (services.length === 0) {
    return (
      <Card>
        <p style={{ fontSize:13, color:"var(--text-secondary)", margin:0 }}>
          Enable a service from the Admin Catalog first, then choose its checklist points here.
        </p>
      </Card>
    );
  }

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
      {services.map(s => {
        const isOpen = openServiceId === s.master_service_id;
        const name = s.tenant_display_name || "Service";
        return (
          <div key={s.tenant_service_id} style={{ display:"flex", flexDirection:"column", gap:12 }}>
            <Card>
              <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", gap:12 }}>
                <div>
                  <div style={{ fontSize:14, fontWeight:700, color:"var(--text-primary)" }}>{name}</div>
                  <div style={{ fontSize:12, color:"var(--text-secondary)", marginTop:2 }}>
                    Choose the points your technicians must complete on every job.
                  </div>
                </div>
                <Btn
                  variant={isOpen ? "secondary" : "primary"}
                  onClick={() => setOpenServiceId(isOpen ? null : s.master_service_id)}
                >
                  {isOpen ? "Close" : "Set up checklist"}
                </Btn>
              </div>
            </Card>
            {isOpen ? (
              <ChecklistSelectionPanel masterServiceId={s.master_service_id} serviceName={name}/>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
