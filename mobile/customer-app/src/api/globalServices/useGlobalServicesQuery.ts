import { useQuery } from "@tanstack/react-query";

import { adaptGlobalService } from "../../domain/globalServices";
import { queryKeys } from "../queryKeys";
import { getGlobalServices } from "./globalServicesApi";


export function useGlobalServicesQuery() {
  return useQuery({
    queryKey: queryKeys.globalServices(),
    queryFn: async () => {
      const response = await getGlobalServices();
      return response.data.map(adaptGlobalService);
    },
    staleTime: 15 * 60 * 1000,
  });
}
