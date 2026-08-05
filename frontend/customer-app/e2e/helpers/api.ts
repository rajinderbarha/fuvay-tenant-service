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

export const CUSTOMER_ONE = { email: 'customer@serviceos.in', password: 'Password123!' };
export const CUSTOMER_TWO = { email: 'customer2@serviceos.in', password: 'Password123!' };

export const SEED = {
  // NOTE: re-pointed to the current live catalog (Final Phase E2E audit,
  // 2026-08-02) -- the category slug is 'air-conditioning' today, not
  // 'home_services' (that string is the tenant VERTICAL key, a different
  // concept from the catalog category slug), and 'ac_repair' no longer
  // exists as an offering slug (today's active offerings are ac-service /
  // ac-gas-refilling / ac-installation). Test-fixture drift, not an
  // application bug -- verify against the live DB if these ever drift again.
  categorySlug: 'air-conditioning',
  offeringSlug: 'ac-service',
  offeringTypeId: 'c86dfcf3-53bd-4d83-bf0b-51257f382652', // Split AC
  brandId: 'a8efc47f-d639-4cf6-a2eb-808f73cad28c', // LG
  city: 'Ludhiana',
  zipcode: '141001',
  issueSummary: 'Not Cooling',
};
