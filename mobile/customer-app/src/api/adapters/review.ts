import { ReviewDto, ReviewEligibilityDto, reviewDtoSchema, reviewEligibilityDtoSchema } from "../contracts/reviews";
import { CustomerReview, ReviewEligibility } from "../../domain/review";
import { asReviewId, asServiceJobId } from "../../domain/ids";
import { REVIEW_ELIGIBILITY_REASONS, ReviewEligibilityReason } from "../../domain/status";
import { parseServerTimestamp } from "../../domain/dates";
import { ContractValidationError, UnknownStatusError } from "../../domain/errors";

export function parseReviewEligibilityDto(raw: unknown): ReviewEligibilityDto {
  const result = reviewEligibilityDtoSchema.safeParse(raw);
  if (!result.success) {
    throw new ContractValidationError("ReviewEligibilityDto", result.error.issues.map(i => i.message));
  }
  return result.data;
}

export function adaptReviewEligibility(dto: ReviewEligibilityDto): ReviewEligibility {
  const reason = dto.reason ?? (dto.eligible ? "eligible" : "job_not_completed");
  if (!(REVIEW_ELIGIBILITY_REASONS as readonly string[]).includes(reason)) {
    throw new UnknownStatusError("reason", reason);
  }
  return { eligible: dto.eligible, reason: reason as ReviewEligibilityReason };
}

export function parseReviewDto(raw: unknown): ReviewDto {
  const result = reviewDtoSchema.safeParse(raw);
  if (!result.success) {
    throw new ContractValidationError("ReviewDto", result.error.issues.map(i => i.message));
  }
  return result.data;
}

export function adaptReview(dto: ReviewDto): CustomerReview {
  return {
    id: asReviewId(dto.id),
    jobId: asServiceJobId(dto.job_id),
    rating: dto.rating,
    comment: dto.comment ?? null,
    createdAt: dto.created_at ? parseServerTimestamp(dto.created_at, "created_at") : null,
  };
}
