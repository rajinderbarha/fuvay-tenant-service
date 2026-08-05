import { ReviewId, ServiceJobId } from "./ids";
import { ReviewEligibilityReason } from "./status";
import { ServerTimestamp } from "./dates";

export interface ReviewEligibility {
  eligible: boolean;
  reason: ReviewEligibilityReason;
}

export interface CustomerReview {
  id: ReviewId;
  jobId: ServiceJobId;
  rating: number;
  comment: string | null;
  createdAt: ServerTimestamp | null;
}
