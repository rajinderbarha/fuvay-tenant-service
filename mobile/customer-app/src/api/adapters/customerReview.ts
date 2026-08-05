import { CustomerReviewDto } from "../contracts/customerReview";
import { CustomerReview } from "../../domain/customerReview";

export function adaptCustomerReview(dto: CustomerReviewDto): CustomerReview {
  return {
    rating: dto.rating,
    comment: dto.comment,
    tags: dto.tags ?? [],
    createdAt: dto.created_at,
  };
}
