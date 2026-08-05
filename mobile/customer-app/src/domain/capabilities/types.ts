import { VerticalKey } from "../catalog";
import { OfflineOperationClass } from "../offline";

export type CapabilityEvidence =
  | "RUNTIME_PROVEN"
  | "SOURCE_VERIFIED"
  | "PARTIAL"
  | "DISCONNECTED"
  | "MISSING"
  | "ROLE_BLOCKED"
  | "VERTICAL_DISABLED"
  | "NOT_APPLICABLE";

export type CustomerCapabilityKey = string;

export interface CustomerCapability {
  key: CustomerCapabilityKey;
  group: string;
  label: string;
  vertical: VerticalKey | "global";
  evidence: CapabilityEvidence;
  requiresAuth: boolean;
  /** The canonical backend route this capability is served by, or the
   * closest verified route if the capability is partial/disconnected.
   * `null` when no route exists at all (MISSING). */
  canonicalEndpoint: string | null;
  /** The backend data model this capability reads/writes, when known. */
  canonicalDataModel: string | null;
  offlinePolicy: OfflineOperationClass | "NOT_APPLICABLE";
  /** Present whenever evidence is anything other than a fully-working
   * state -- a short, factual description of what's wrong, never a
   * customer-facing string. */
  blocker?: string;
  /** Source this phase's classification came from -- keeps the registry
   * honest about its own evidence tier. */
  verificationSource: "live_openapi_introspection" | "router_source_read" | "model_source_read" | "not_verified";
  /** Whether Phase E or a later phase may expose this to UI. A screen
   * must never expose a capability whose flag here is false. */
  exposableInUi: boolean;
}
