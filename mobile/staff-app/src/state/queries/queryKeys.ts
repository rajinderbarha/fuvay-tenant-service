/**
 * Central, stable query-key factory (Phase F spec section 17, built out
 * now that Phase H is the first phase with real feature data). Every
 * feature query key is scoped by tenantId/technicianId so:
 *   - a session/tenant switch can never surface the previous session's
 *     cached data (queryClient.removeQueries keyed on these prefixes),
 *   - search/filter/view state is part of the key wherever a screen has it
 *     (Phase I's Jobs directory uses this same factory).
 */
export const queryKeys = {
  public: () => ["public"] as const,

  session: () => ["session"] as const,

  technician: {
    all: (tenantId: string, technicianId: string) => ["technician", tenantId, technicianId] as const,
    home: (tenantId: string, technicianId: string) => ["technician", tenantId, technicianId, "home"] as const,
  },

  tenant: {
    all: (tenantId: string) => ["tenant", tenantId] as const,
  },

  jobs: {
    all: (tenantId: string, technicianId: string) => ["jobs", tenantId, technicianId] as const,
    list: (tenantId: string, technicianId: string, params: Record<string, unknown>) =>
      ["jobs", tenantId, technicianId, "list", params] as const,
    detail: (tenantId: string, technicianId: string, jobId: string) =>
      ["jobs", tenantId, technicianId, "detail", jobId] as const,
  },

  notifications: {
    all: (tenantId: string, technicianId: string) => ["notifications", tenantId, technicianId] as const,
    unreadCount: (tenantId: string, technicianId: string) =>
      ["notifications", tenantId, technicianId, "unread-count"] as const,
  },
};
