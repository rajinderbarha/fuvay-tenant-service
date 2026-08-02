import { getAccessContext as fetchAccessContextDTO } from "./authApi";
import { AccessContextDTO } from "./types";
import { AccessContext, CanonicalRole, Audience } from "../../navigation/guards/types";

/**
 * Maps the backend's real access-context projection onto Phase E's
 * existing `AccessContext` type (navigation/guards/types.ts) -- reusing
 * that contract rather than inventing a second, competing shape. This is
 * the ONLY place the DTO's snake_case fields become the route guards'
 * camelCase fields.
 */
const KNOWN_ROLES: ReadonlySet<string> = new Set<CanonicalRole>([
  "super_admin", "admin_operations", "admin_finance", "admin_security", "admin_readonly",
  "tenant_owner", "staff", "technician", "customer", "guest",
]);
const KNOWN_AUDIENCES: ReadonlySet<string> = new Set<Audience>([
  "serviceos:admin", "serviceos:tenant", "serviceos:staff", "serviceos:customer",
]);

export function mapAccessContextDTO(dto: AccessContextDTO, sessionExpiry?: string): AccessContext {
  return {
    authenticated: true,
    userId: dto.user_id,
    canonicalRole: KNOWN_ROLES.has(dto.canonical_role) ? (dto.canonical_role as CanonicalRole) : undefined,
    audience: KNOWN_AUDIENCES.has(dto.audience) ? (dto.audience as Audience) : undefined,
    tenantId: dto.tenant_id ?? undefined,
    tenantStatus: dto.tenant_status ?? undefined,
    technicianId: dto.technician_id ?? undefined,
    technicianStatus: dto.technician_status ?? undefined,
    enabledVerticals: dto.enabled_verticals,
    capabilities: dto.capabilities,
    sessionExpiry,
  };
}

export async function fetchMappedAccessContext(sessionExpiry?: string) {
  const result = await fetchAccessContextDTO();
  if (!result.ok) return result;
  return { ok: true as const, data: mapAccessContextDTO(result.data, sessionExpiry), meta: result.meta };
}
