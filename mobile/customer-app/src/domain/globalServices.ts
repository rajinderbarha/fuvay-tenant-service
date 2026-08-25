import { z } from "zod";

import { globalServiceDtoSchema } from "../api/contracts/globalServices";


export interface GlobalService {
  id: string;
  name: string;
  tagline: string | null;
  description: string | null;
  iconUrl: string | null;
}

export function adaptGlobalService(dto: z.infer<typeof globalServiceDtoSchema>): GlobalService {
  return {
    id: dto.id,
    name: dto.name,
    tagline: dto.tagline,
    description: dto.description,
    iconUrl: dto.icon_url,
  };
}
