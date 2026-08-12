import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { bookingQueryKeys } from "../customerBookings/bookingQueryKeys";
import {
  acknowledgeCustomerHandover,
  confirmCustomerDirectPayment,
  getCustomerHandover,
  listCustomerDirectPayments,
  reportCustomerDirectPaymentNotPaid,
} from "./customerClosureApi";

const handoverKey = (jobId: string) => ["customer", "job-closure", jobId, "handover"] as const;
const paymentsKey = ["customer", "direct-payments"] as const;

export function useCustomerClosureQueries(jobId: string, bookingId: string, enabled: boolean) {
  const queryClient = useQueryClient();
  const handover = useQuery({
    queryKey: handoverKey(jobId),
    queryFn: async () => (await getCustomerHandover(jobId)).data,
    enabled,
  });
  const payments = useQuery({
    queryKey: paymentsKey,
    queryFn: async () => (await listCustomerDirectPayments()).data,
    enabled,
  });
  const refreshClosure = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: handoverKey(jobId) }),
      queryClient.invalidateQueries({ queryKey: paymentsKey }),
      queryClient.invalidateQueries({ queryKey: bookingQueryKeys.detail(bookingId) }),
    ]);
  };
  const acknowledge = useMutation({
    mutationFn: () => acknowledgeCustomerHandover(jobId),
    onSuccess: refreshClosure,
  });
  const confirmPayment = useMutation({
    mutationFn: (paymentId: string) => confirmCustomerDirectPayment(paymentId),
    onSuccess: refreshClosure,
  });
  const reportNotPaid = useMutation({
    mutationFn: (paymentId: string) => reportCustomerDirectPaymentNotPaid(paymentId),
    onSuccess: refreshClosure,
  });
  const payment = payments.data?.items.find(item => item.job_id === jobId) ?? null;
  return { handover, payments, payment, acknowledge, confirmPayment, reportNotPaid };
}
