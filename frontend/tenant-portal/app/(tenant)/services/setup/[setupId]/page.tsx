"use client";
import React, { useCallback, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { WizardShell, WizardFooter, WizardStep } from "../../../../../components/service-setup/WizardShell";
import { CoveragePricingStep } from "../../../../../components/service-setup/CoveragePricingStep";
import { ReviewPublishStep } from "../../../../../components/service-setup/ReviewPublishStep";
import { useApi } from "../../../../../hooks/useApi";
import { serviceSetupApi } from "../../../../../lib/api";
import { Btn, Skeleton } from "../../../../../components/shared/ui";

/** Continues setup for an already-enabled tenant_service (Steps 3-5: Job
 * Types confirmation, Coverage & Pricing, Review & Publish). Category and
 * Service (Steps 1-2) were already resolved when this tenant_service was
 * created via /services/setup/new. */
export default function ContinueServiceSetupPage() {
  const params = useParams<{ setupId: string }>();
  const router = useRouter();
  const tsid = params.setupId;
  type Step = Extract<WizardStep, "job-types" | "coverage-pricing" | "review">;
  const VALID_STEPS: Step[] = ["job-types", "coverage-pricing", "review"];
  const [step, setStep] = useState<Step>("job-types");
  const [resumed, setResumed] = useState(false);
  const [publishedSuccess, setPublishedSuccess] = useState(false);

  const serviceRes = useApi(useCallback(() => serviceSetupApi.getEnabledService(tsid), [tsid]));
  const service = serviceRes.data;

  // Resume from the last step the tenant was on (spec: "leave and resume").
  // Runs once, the first time the service loads.
  React.useEffect(() => {
    if (!resumed && service?.last_active_step && VALID_STEPS.includes(service.last_active_step as Step)) {
      setStep(service.last_active_step as Step);
    }
    if (service) setResumed(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [service]);

  async function persistStep(next: Step) {
    setStep(next);
    try { await serviceSetupApi.updateWizardStep(tsid, next); } catch { /* best-effort resume pointer */ }
  }

  async function handleSaveAndExit() {
    try { await serviceSetupApi.updateWizardStep(tsid, step); } catch { /* best-effort */ }
    router.push("/services");
  }

  if (serviceRes.loading || !service) {
    return (
      <WizardShell currentStep="job-types">
        <Skeleton height={300} />
      </WizardShell>
    );
  }
  if (serviceRes.error) {
    return (
      <WizardShell currentStep="job-types">
        <p style={{ color: "var(--danger-text)", fontSize: 13 }}>{serviceRes.error}</p>
        <Btn onClick={() => router.push("/services")} style={{ marginTop: 12 }}>Back to Services</Btn>
      </WizardShell>
    );
  }

  if (publishedSuccess) {
    return (
      <WizardShell currentStep="review" breadcrumb={service.tenant_display_name ?? undefined}>
        <div style={{ textAlign: "center", padding: "40px 0", display: "flex", flexDirection: "column", gap: 16, alignItems: "center" }}>
          <div style={{ width: 56, height: 56, borderRadius: "50%", background: "var(--success-bg)",
            display: "flex", alignItems: "center", justifyContent: "center", fontSize: 28 }}>✓</div>
          <h1 style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>Service published</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
            {service.tenant_display_name || "Your service"} is now live for customers.
          </p>
          <div style={{ display: "flex", gap: 10, marginTop: 8 }}>
            <Btn variant="secondary" onClick={() => router.push(`/services/setup/${tsid}`)}>View Service</Btn>
            <Btn variant="secondary" onClick={() => router.push("/services/setup/new")}>Add Another Service</Btn>
            <Btn onClick={() => router.push("/services")}>Return to Services</Btn>
          </div>
        </div>
      </WizardShell>
    );
  }

  return (
    <WizardShell currentStep={step} breadcrumb={service.tenant_display_name ?? undefined}
      onSaveAndExit={handleSaveAndExit}>
      {step === "job-types" && (
        <>
          <h1 style={{ fontSize: 20, fontWeight: 800, margin: "0 0 4px" }}>Confirm this service</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 20px" }}>
            Job type: <strong>{service.job_type}</strong>.{" "}
            {service.requires_type && service.requires_brand
              ? "This service uses both Type and Brand."
              : service.requires_type
              ? "This service uses Type only."
              : service.requires_brand
              ? "This service uses Brand only."
              : "This service has no Type or Brand -- just set your price in the next step."}
          </p>
          <WizardFooter onBack={() => router.push("/services")} onContinue={() => persistStep("coverage-pricing")}
            continueLabel="Continue: Coverage & Pricing" />
        </>
      )}
      {step === "coverage-pricing" && (
        <>
          <CoveragePricingStep service={service} onRefetchService={serviceRes.refetch} />
          <WizardFooter onBack={() => persistStep("job-types")} onContinue={() => persistStep("review")}
            continueLabel="Continue: Review" />
        </>
      )}
      {step === "review" && (
        <>
          <ReviewPublishStep service={service} onPublished={() => setPublishedSuccess(true)} />
          <WizardFooter onBack={() => persistStep("coverage-pricing")} />
        </>
      )}
    </WizardShell>
  );
}
