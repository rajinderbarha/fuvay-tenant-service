"use client";
import React, { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { WizardShell, WizardFooter } from "../../../../../components/service-setup/WizardShell";
import { CategorySelector } from "../../../../../components/service-setup/CategorySelector";
import { ServiceSelector } from "../../../../../components/service-setup/ServiceSelector";
import { useApi, useAction } from "../../../../../hooks/useApi";
import {
  serviceSetupApi, type MyVerticalEnrollment, type AdminMasterServiceRow,
} from "../../../../../lib/api";

/** New-service entry flow: Category -> Service -> enable -> redirect into
 * the setup wizard proper ([setupId]) for Job Types / Coverage & Pricing /
 * Review. Schema-driven: no vertical, service, type or brand is hardcoded --
 * everything renders from GET /v1/tenant/vertical-enrollments and the
 * tenant's real entitlement-filtered available-services list. */
export default function NewServiceSetupPage() {
  const router = useRouter();
  const [step, setStep] = useState<"category" | "service">("category");
  const [selectedVertical, setSelectedVertical] = useState<MyVerticalEnrollment | null>(null);
  const [selectedService, setSelectedService] = useState<AdminMasterServiceRow | null>(null);
  const [error, setError] = useState<string | null>(null);

  const verticalsRes = useApi(useCallback(() => serviceSetupApi.getMyVerticalEnrollments(), []), []);
  const availableRes = useApi(useCallback(() => serviceSetupApi.listAvailableServices(), []), []);
  const enabledRes = useApi(useCallback(() => serviceSetupApi.listEnabledServices(), []), []);

  const verticals = verticalsRes.data?.verticals ?? [];
  // Services list isn't vertical-scoped by a shared key on this endpoint
  // today (available-services is already entitlement-filtered server-side
  // to the tenant's approved category), so once exactly one vertical
  // exists it's auto-selected -- avoids an unnecessary screen per spec.
  const services = availableRes.data?.services ?? [];

  const enableAction = useAction(useCallback(async (service: AdminMasterServiceRow) => {
    if (!service.job_type_id) throw new Error("This service has no job type configured.");
    const existing = (enabledRes.data?.services ?? []).find(s => s.master_service_id === service.service_id && s.job_type_id === service.job_type_id);
    if (existing) return existing; // never create a duplicate tenant setup for the same service
    return serviceSetupApi.enableService(service.service_id, service.job_type_id);
  }, [enabledRes.data]));

  async function handleContinueFromService() {
    if (!selectedService) return;
    setError(null);
    const result = await enableAction.execute(selectedService);
    if (result) {
      router.push(`/services/setup/${result.tenant_service_id}`);
    } else if (enableAction.error) {
      setError(enableAction.error);
    }
  }

  React.useEffect(() => {
    if (step === "category" && verticals.length === 1 && !selectedVertical) {
      setSelectedVertical(verticals[0]);
    }
  }, [step, verticals, selectedVertical]);

  return (
    <WizardShell currentStep={step === "category" ? "category" : "service"}
      breadcrumb={selectedVertical?.vertical_label}>
      {step === "category" && (
        <>
          {verticalsRes.loading ? <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Loading…</p> : (
            <CategorySelector verticals={verticals} selectedVerticalId={selectedVertical?.vertical_id ?? null}
              onSelect={setSelectedVertical} />
          )}
          <WizardFooter onContinue={() => setStep("service")} continueDisabled={!selectedVertical}
            continueLabel="Continue: Select Service" />
        </>
      )}
      {step === "service" && (
        <>
          {availableRes.loading ? <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Loading…</p> : (
            <ServiceSelector services={services} selectedServiceId={selectedService?.service_id ?? null}
              onSelect={setSelectedService} />
          )}
          {error && <p style={{ color: "var(--danger-text)", fontSize: 13, marginTop: 12 }}>{error}</p>}
          <WizardFooter onBack={() => setStep("category")} onContinue={handleContinueFromService}
            continueDisabled={!selectedService} continueLoading={enableAction.loading}
            continueLabel="Continue: Job Types" />
        </>
      )}
    </WizardShell>
  );
}
