"use client";
/**
 * Read-only view of the Problems / Questions / Checklists the PLATFORM has
 * attached to one of this tenant's enabled services.
 *
 * Closes a real visibility gap found in the admin<->tenant connectivity
 * audit: admin authors these per (master service, job type) in the Catalog
 * Workspace, and they decide what the customer is asked at booking and what
 * the technician must complete on site -- but the tenant, who trains that
 * technician and sets the customer's expectations, could not see any of it.
 * Only the customer app and the technician app consumed them.
 *
 * Deliberately read-only: these are centrally owned so every provider is
 * asked the same qualifying questions for the same service. The backend
 * enforces that too (tenant_editable is always false, and it 403s for a
 * service this tenant hasn't enabled) -- this component never offers an edit
 * affordance it couldn't honour.
 */
import React, { useCallback } from "react";
import { ClipboardList, HelpCircle, AlertTriangle, Camera, Info, PackagePlus } from "lucide-react";
import { masterCatalogApi, type ServiceRequirements } from "../../lib/api";
import { useApi } from "../../hooks/useApi";

const SECTION: React.CSSProperties = { marginTop: 16 };
const HEAD: React.CSSProperties = {
  display: "flex", alignItems: "center", gap: 7, marginBottom: 8,
  fontSize: 13, fontWeight: 700, color: "var(--text-primary)",
};
const ROW: React.CSSProperties = {
  padding: "8px 0", borderTop: "1px solid var(--border)", fontSize: 13,
};
const CHIP: React.CSSProperties = {
  fontSize: 10, fontWeight: 600, padding: "1px 6px", borderRadius: 4,
  background: "var(--surface-sunken)", color: "var(--text-tertiary)",
};

export function ServiceRequirementsPanel({ masterServiceId, jobTypeId }: { masterServiceId: string; jobTypeId: string }) {
  const req = useApi(
    useCallback(() => masterCatalogApi.getServiceRequirements(masterServiceId, jobTypeId), [masterServiceId, jobTypeId]),
    [masterServiceId, jobTypeId],
  );
  const d = req.data as ServiceRequirements | undefined;

  if (req.loading) {
    return <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Loading requirements…</p>;
  }
  if (req.error || !d) {
    return (
      <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
        Requirements for this service could not be loaded.
      </p>
    );
  }

  const serviceOptions = d.service_options ?? [];
  const empty = d.problems.length === 0 && d.questions.length === 0 && serviceOptions.length === 0 && d.checklists.length === 0;

  return (
    <div>
      <div style={{ display: "flex", gap: 8, padding: "8px 10px", borderRadius: 8,
        background: "var(--surface-sunken)", border: "1px solid var(--border)" }}>
        <Info size={14} style={{ color: "var(--text-tertiary)", flexShrink: 0, marginTop: 1 }} />
        <span style={{ fontSize: 11.5, color: "var(--text-secondary)" }}>{d.note}</span>
      </div>

      {empty && (
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 14 }}>
          No problems, options, questions or checklists have been configured for this service yet.
        </p>
      )}

      {serviceOptions.length > 0 && (
        <div style={SECTION}>
          <div style={HEAD}>
            <PackagePlus size={14} style={{ color: "var(--brand)" }} />
            Options and add-ons ({serviceOptions.length})
          </div>
          {serviceOptions.map(option => (
            <div key={option.mapping_id} style={ROW}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                <span style={{ color: "var(--text-primary)" }}>{option.name ?? "—"}</span>
                {option.usage && <span style={CHIP}>{option.usage}</span>}
                {option.customer_selectable && <span style={CHIP}>CUSTOMER</span>}
                {option.technician_selectable && <span style={CHIP}>TECHNICIAN</span>}
                {option.quantity_supported && <span style={CHIP}>QUANTITY · {option.measurement_unit ?? "unit"}</span>}
              </div>
              {option.description && (
                <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: "2px 0 0" }}>{option.description}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {d.problems.length > 0 && (
        <div style={SECTION}>
          <div style={HEAD}>
            <AlertTriangle size={14} style={{ color: "var(--warning-text)" }} />
            Problems the customer can report ({d.problems.length})
          </div>
          {d.problems.map(p => (
            <div key={p.issue_type_id} style={ROW}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                <span style={{ color: "var(--text-primary)" }}>{p.name ?? "—"}</span>
                {p.is_common && <span style={CHIP}>COMMON</span>}
                {p.severity && <span style={CHIP}>{String(p.severity).toUpperCase()}</span>}
                {p.requires_photo && (
                  <span style={{ ...CHIP, display: "inline-flex", alignItems: "center", gap: 3 }}>
                    <Camera size={9} /> PHOTO REQUIRED
                  </span>
                )}
              </div>
              {p.description && (
                <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: "2px 0 0" }}>{p.description}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {d.questions.length > 0 && (
        <div style={SECTION}>
          <div style={HEAD}>
            <HelpCircle size={14} style={{ color: "var(--brand)" }} />
            Questions asked at booking ({d.questions.length})
          </div>
          {d.questions.map(q => (
            <div key={q.question_id} style={ROW}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                <span style={{ color: "var(--text-primary)" }}>{q.label ?? "—"}</span>
                {q.required && <span style={{ ...CHIP, color: "var(--danger-text)" }}>REQUIRED</span>}
                {q.input_type && <span style={CHIP}>{q.input_type}</span>}
                {q.customer_visible === false && <span style={CHIP}>INTERNAL</span>}
              </div>
              {q.options.length > 0 && (
                <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: "2px 0 0" }}>
                  Options: {q.options.filter(Boolean).join(", ")}
                </p>
              )}
              {q.help_text && (
                <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: "2px 0 0" }}>{q.help_text}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {d.checklists.length > 0 && (
        <div style={SECTION}>
          <div style={HEAD}>
            <ClipboardList size={14} style={{ color: "var(--success-text)" }} />
            Checklists your technician must complete ({d.checklists.length})
          </div>
          {d.checklists.map(c => (
            <div key={c.mapping_id} style={ROW}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                <span style={{ color: "var(--text-primary)" }}>{c.template_name}</span>
                {c.purpose && <span style={CHIP}>{String(c.purpose).replace(/_/g, " ")}</span>}
                {c.phase && <span style={CHIP}>{String(c.phase).replace(/_/g, " ")}</span>}
                <span style={CHIP}>v{c.version_number}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
