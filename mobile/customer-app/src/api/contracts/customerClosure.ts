import { z } from "zod";

export const customerHandoverSchema = z.object({
  job_id: z.string(),
  status: z.enum(["not_requested", "requested", "customer_unavailable", "acknowledged"]),
  requested_at: z.string().nullable(),
  can_acknowledge: z.boolean(),
});

export const customerDirectPaymentSchema = z.object({
  payment_id: z.string(),
  job_id: z.string(),
  booking_id: z.string().nullable(),
  job_ref: z.string().nullable(),
  provider_business: z.string().nullable(),
  service_amount: z.string(),
  currency: z.string(),
  method: z.string(),
  payment_date: z.string().nullable(),
  evidence_available: z.boolean(),
  status: z.string(),
  customer_confirmed: z.boolean(),
  customer_action: z.string().nullable(),
  notice: z.string(),
});

export const customerDirectPaymentsSchema = z.object({
  items: z.array(customerDirectPaymentSchema),
  total: z.number(),
});

export const customerPaymentDecisionSchema = z.object({
  payment_id: z.string(),
  status: z.string(),
}).passthrough();

export const customerHandoverMutationSchema = z.object({
  handover_status: z.enum(["requested", "customer_unavailable", "acknowledged"]),
}).passthrough();

export type CustomerHandover = z.infer<typeof customerHandoverSchema>;
export type CustomerDirectPayment = z.infer<typeof customerDirectPaymentSchema>;
