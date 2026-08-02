import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../../services/support/supportApi";
import * as employmentApi from "../../services/employment/employmentApi";
import { AppError } from "../../services/api/types";

const WORKSPACE_KEY = ["help-workspace"] as const;

/** Help & Support hub (Phase Y). Reuses the existing real Tenant Help &
 * Support workspace projection + Phase S's employment-details endpoint for
 * manager contact -- never a fabricated support-team directory. */
export function useHelpWorkspace() {
  const queryClient = useQueryClient();

  const workspace = useQuery({
    queryKey: WORKSPACE_KEY,
    queryFn: async ({ signal }) => {
      const result = await api.getWorkspace(signal);
      if (!result.ok) throw result.error;
      return result.data;
    },
  });

  const manager = useQuery({
    queryKey: ["employment-manager-contact"],
    queryFn: async ({ signal }) => {
      const result = await employmentApi.getEmploymentDetails();
      if (!result.ok) throw result.error;
      return result.data.employment?.reports_to ?? null;
    },
  });

  return {
    data: workspace.data,
    isLoading: workspace.isLoading,
    isError: workspace.isError,
    error: workspace.error as AppError | null,
    isRefetching: workspace.isRefetching,
    refetch: workspace.refetch,
    manager: manager.data,
    invalidate: () => queryClient.invalidateQueries({ queryKey: WORKSPACE_KEY }),
  };
}
