import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getBookingRating, submitBookingRating, SubmitRatingInput } from "./customerReviewApi";
import { adaptCustomerReview } from "../adapters/customerReview";

const reviewKey = (bookingId: string) => ["customer-review", bookingId] as const;

export function useBookingReviewQuery(bookingId: string, enabled: boolean) {
  return useQuery({
    queryKey: reviewKey(bookingId),
    queryFn: async () => {
      const res = await getBookingRating(bookingId);
      return res.data.review ? adaptCustomerReview(res.data.review) : null;
    },
    enabled,
  });
}

export function useSubmitBookingRatingMutation(bookingId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: SubmitRatingInput) => adaptCustomerReview((await submitBookingRating(bookingId, input)).data.review),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: reviewKey(bookingId) }),
  });
}
