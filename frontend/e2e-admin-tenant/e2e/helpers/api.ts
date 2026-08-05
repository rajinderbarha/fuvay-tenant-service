// Direct backend API helpers for E2E seeding/verification (real HTTP, no mocking).
const API_BASE = process.env.E2E_API_BASE || 'http://localhost:8000';

export async function login(email: string, password: string): Promise<string> {
  const res = await fetch(`${API_BASE}/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(`login failed: ${res.status} ${await res.text()}`);
  const json = await res.json();
  return json.data.access_token as string;
}

export async function apiGet(path: string, token: string) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return { status: res.status, body: await res.json() };
}

export async function apiPost(path: string, token: string, body?: unknown) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: body ? JSON.stringify(body) : undefined,
  });
  return { status: res.status, body: await res.json() };
}

export async function apiPut(path: string, token: string, body: unknown) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  });
  return { status: res.status, body: await res.json() };
}

export const SUPER_ADMIN = { email: 'admin@serviceos.in', password: 'Password123!' };
export const ADMIN_OPERATOR = { email: 'admin.operator@serviceos.in', password: 'Password123!' };
export const TENANT_OWNER = { email: 'provider@serviceos.in', password: 'Password123!' };
export const TENANT_MANAGER = { email: 'tenant.manager@serviceos.in', password: 'Password123!' };
export const TENANT_READONLY = { email: 'tenant.readonly@serviceos.in', password: 'Password123!' };
export const STAFF_ONE = { email: 'staff@serviceos.in', password: 'Password123!' };
export const CUSTOMER_ONE = { email: 'customer@serviceos.in', password: 'Password123!' };
export const CUSTOMER_TWO = { email: 'customer2@serviceos.in', password: 'Password123!' };

export const SEED = {
  // Re-pointed 2026-08-05 (second occurrence of the same drift -- see the
  // 2026-08-02 note this replaces). The previously-referenced "Demo AC
  // Services" tenant 5209ef33 no longer exists, nor did the master service
  // "AC Repair", the 3958 credit balance, or the 21-credit deduction rule
  // that several specs asserted on. Every one of those failures was
  // test-fixture drift, NOT an application bug: the specs were pinned to a
  // dataset a DB reseed removed.
  //
  // These values were read out of the live DB (verified present at the time
  // of writing), and deliberately point at the ONE tenant that has real
  // data to assert against -- 11 enabled services, 11 jobs, an active
  // home_services enrollment. If these fail again with 404/NOT_FOUND at the
  // seed step, re-verify against the DB rather than assuming a code
  // regression.
  //
  // NOT re-seeded on purpose: scripts/seed_ac_repair_baseline_mappings.py
  // expects a ServiceCategory *slugged* "home_services", but this schema
  // models categories as the services themselves (air-conditioning,
  // plumbing, ...) with "home_services" living in vertical_type. Creating
  // such a category to satisfy the old fixture would risk re-scoping
  // TenantCatalogService.get_home_services_category_id(), which takes the
  // FIRST vertical_type == 'home_services' row -- i.e. it could silently
  // repoint the tenant Service Setup wizard at an empty category.
  tenantId: '244beeec-fedc-452e-8054-317e45557d4d',
  tenantName: 'Guramrit',
  categorySlug: 'air-conditioning',
  offeringSlug: 'ac-service',
  // Display name as rendered in the admin catalog UI. Specs used to
  // hardcode 'AC Repair', a master service that no longer exists; the live
  // equivalent carrying the Split AC / LG / AC-Not-Cooling relationships is
  // 'AC Service'.
  offeringName: 'AC Service',
  offeringTypeId: 'cf1b20e5-162a-4e8e-b0e1-262c014413a6', // Split AC
  brandId: 'a8efc47f-d639-4cf6-a2eb-808f73cad28c', // LG (unchanged, still live)
  // Guramrit's actual declared service area -- was Ludhiana/141001, which
  // belonged to the removed tenant. A serviceability check against the old
  // pair fails before any UI assertion runs.
  city: 'BASSIPATHANA',
  zipcode: '140412',
  // Real, active issue on ac-service ("Not Cooling" did not exist).
  issueSummary: 'AC Not Cooling',
};
