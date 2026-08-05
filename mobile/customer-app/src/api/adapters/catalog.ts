import { CategoryDto, categoryDtoSchema } from "../contracts/catalog";
import { Category, VerticalKey } from "../../domain/catalog";
import { asCategoryId } from "../../domain/ids";
import { ContractValidationError } from "../../domain/errors";

const KNOWN_VERTICALS: readonly VerticalKey[] = ["home_services", "coaching", "real_estate"];

export function parseCategoryDto(raw: unknown): CategoryDto {
  const result = categoryDtoSchema.safeParse(raw);
  if (!result.success) {
    throw new ContractValidationError("CategoryDto", result.error.issues.map(i => i.message));
  }
  return result.data;
}

/** An unrecognized vertical string is normalized to `null` (hidden),
 * never guessed -- this is deliberately more lenient than
 * UnknownStatusError's hard failure because a new vertical the backend
 * enables ahead of a client update should fail SAFE (hidden), not crash
 * the whole category list. */
export function adaptCategory(dto: CategoryDto): Category {
  const vertical = dto.vertical && (KNOWN_VERTICALS as readonly string[]).includes(dto.vertical)
    ? (dto.vertical as VerticalKey)
    : null;
  return {
    id: asCategoryId(dto.id),
    slug: dto.slug,
    name: dto.name,
    vertical,
    isActive: dto.is_active ?? true,
  };
}
