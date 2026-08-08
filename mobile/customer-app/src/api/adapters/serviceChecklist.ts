import { z } from "zod";
import { serviceChecklistResponseSchema } from "../contracts/serviceChecklist";
import { ServiceChecklist } from "../../domain/serviceChecklist";

type Dto = z.infer<typeof serviceChecklistResponseSchema>;

/** Maps the backend shape onto the domain type. Sections with no points are
 * dropped: an empty heading is noise, not information. */
export function adaptServiceChecklist(dto: Dto): ServiceChecklist {
  return {
    totalPoints: dto.total_points,
    photoPoints: dto.photo_points,
    providerSelected: dto.provider_selected,
    sections: dto.sections
      .map(section => ({
        title: section.title,
        points: section.points.map(point => ({
          id: point.id,
          label: point.label,
          helpText: point.help_text ?? null,
          requiresPhoto: point.requires_photo,
        })),
      }))
      .filter(section => section.points.length > 0),
  };
}
