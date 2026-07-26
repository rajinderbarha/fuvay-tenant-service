"use client";
import React, { useCallback } from "react";
import { useApi, useAction } from "../../hooks/useApi";
import { serviceSetupApi, type TenantEnabledService } from "../../lib/api";
import { Btn, Badge, Skeleton } from "../shared/ui";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { PricingResolutionTest } from "./PricingResolutionTest";

/** Step 5: Review & Publish. Calls the real backend publish-validation
 * endpoint and renders field-level errors grouped by step/job-type/
 * dimension -- never a single generic "invalid configuration" banner. */
export function ReviewPublishStep({ service, onPublished }: {
  service: TenantEnabledService; onPublished: () => void;
}) {
  const tsid = service.tenant_service_id;
  const validationRes = useApi(useCallback(() => serviceSetupApi.validateForPublish(tsid), [tsid]));
  const blueprintRes = useApi(useCallback(() => serviceSetupApi.getBlueprintUpdateStatus(tsid), [tsid]));

  const publishAction = useAction(useCallback(async () => {
    const result = await serviceSetupApi.validateForPublish(tsid);
    if (!result.valid) throw new Error("Cannot publish -- resolve the issues below first.");
    return serviceSetupApi.publish(tsid);
  }, [tsid]));

  async function handlePublish() {
    const result = await publishAction.execute();
    if (result) onPublished();
  }

  const errors = validationRes.data?.errors ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div>
        <h2 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 4px" }}>Review your setup</h2>
        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
          {service.tenant_display_name || "This service"} · Job type: {service.job_type}
        </p>
      </div>

      {blueprintRes.data?.update_required && (
        <div style={{ padding: 14, borderRadius: 10, background: "var(--warning-bg)", border: "1px solid var(--warning-border)" }}>
          <p style={{ margin: "0 0 6px", fontSize: 13, fontWeight: 700, color: "var(--warning-text)" }}>
            Service configuration update required
          </p>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "var(--warning-text)" }}>
            {blueprintRes.data.changes.map((c, i) => <li key={i}>{c}</li>)}
          </ul>
        </div>
      )}

      <div>
        <h3 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 8px" }}>Coverage</h3>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {service.requires_type && <Badge variant="muted">Type-based</Badge>}
          {service.requires_brand && <Badge variant="muted">Brand-based</Badge>}
          {!service.requires_type && !service.requires_brand && <Badge variant="muted">Simple service</Badge>}
        </div>
      </div>

      <div>
        <h3 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 8px" }}>Pricing</h3>
        <p style={{ fontSize: 13, margin: 0 }}>
          {service.tenant_min_price != null
            ? `Default: ₹${service.tenant_min_price}–₹${service.tenant_max_price}`
            : service.tenant_visit_fee != null
            ? `Visit fee: ₹${service.tenant_visit_fee}`
            : "Not configured"}
        </p>
      </div>

      <PricingResolutionTest service={service} />

      {/* Validation summary -- field-level errors, grouped, not a generic banner */}
      <div role="alert" aria-live="polite">
        <h3 style={{ fontSize: 13, fontWeight: 700, margin: "0 0 8px" }}>Publish readiness</h3>
        {validationRes.loading ? <Skeleton height={60} /> : errors.length === 0 ? (
          <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--success-text)", fontSize: 13 }}>
            <CheckCircle2 size={16} /> Everything looks ready to publish.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {errors.map((e, i) => (
              <div key={i} style={{ display: "flex", gap: 8, padding: "10px 12px", borderRadius: 8,
                background: "var(--danger-bg)", border: "1px solid var(--danger-border)" }}>
                <AlertTriangle size={15} color="var(--danger-text)" style={{ flexShrink: 0, marginTop: 1 }} />
                <div>
                  <p style={{ margin: 0, fontSize: 12, fontWeight: 600, color: "var(--danger-text)" }}>
                    {e.step}{Object.keys(e.dimension_path).length > 0
                      ? ` · ${Object.entries(e.dimension_path).map(([k, v]) => `${k}: ${v}`).join(", ")}`
                      : ""}
                  </p>
                  <p style={{ margin: 0, fontSize: 12, color: "var(--danger-text)" }}>{e.message}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {publishAction.error && <p style={{ color: "var(--danger-text)", fontSize: 13 }}>{publishAction.error}</p>}

      <Btn onClick={handlePublish} disabled={errors.length > 0} loading={publishAction.loading}>
        Publish Service
      </Btn>
    </div>
  );
}
