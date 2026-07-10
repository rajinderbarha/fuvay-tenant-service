// Deterministic-state helpers for E2E. Verifies (does not fabricate) that the
// baseline AC Repair / Split AC / LG / Ludhiana 141001 scenario is bookable,
// by calling the REAL backend APIs the app itself uses. See
// CUSTOMER_FRONTEND_02B_SEED_DATA_REPORT.md for how the underlying DB state
// was produced (one tenant.status fix + 1 cloned customer row).
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
}
