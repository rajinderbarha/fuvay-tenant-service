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
  tenantId: '34b427a7-b2be-496c-b826-6d51bb181248',
  tenantName: 'Demo AC Services',
  categorySlug: 'home_services',
  offeringSlug: 'ac_repair',
  offeringTypeId: 'c86dfcf3-53bd-4d83-bf0b-51257f382652', // Split AC
  brandId: '64a3b25f-23aa-4639-8baf-f67def0f60db', // LG
  city: 'Ludhiana',
  zipcode: '141001',
  issueSummary: 'Not Cooling',
};
