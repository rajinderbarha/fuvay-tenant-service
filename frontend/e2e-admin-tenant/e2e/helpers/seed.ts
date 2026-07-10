// Verifies (does not fabricate) that the Demo AC Services baseline is bookable,
// by calling the REAL backend APIs. See ADMIN_TENANT_E2E_01_TENANT_SEED_DATA_REPORT.md
// for the full verification of this tenant's state.
import { login, apiPost, apiPut, CUSTOMER_ONE, SEED } from './api';

export async function ensureBaselineBookable(): Promise<void> {
  const token = await login(CUSTOMER_ONE.email, CUSTOMER_ONE.password);
  const draft = await apiPost('/v1/customer/home-services/booking-drafts', token, {
    category_slug: SEED.categorySlug,
    offering_slug: SEED.offeringSlug,
  });
  if (draft.status !== 200) throw new Error(`seed check: draft create failed ${JSON.stringify(draft.body)}`);
  const draftId = draft.body.data.id;

  await apiPut(`/v1/customer/home-services/booking-drafts/${draftId}`, token, {
    issue_summary: SEED.issueSummary,
    city: SEED.city,
    zipcode: SEED.zipcode,
    offering_type_id: SEED.offeringTypeId,
    brand_id: SEED.brandId,
  });

  const match = await apiPost(`/v1/customer/home-services/booking-drafts/${draftId}/match-and-price`, token);
  if (match.status !== 200 || !match.body?.data?.selected_provider) {
    throw new Error(`seed check: baseline scenario is NOT bookable — ${JSON.stringify(match.body)}`);
  }
  if (match.body.data.selected_provider.tenant_id !== SEED.tenantId) {
    throw new Error(`seed check: unexpected tenant matched — ${match.body.data.selected_provider.tenant_id}`);
  }
}
