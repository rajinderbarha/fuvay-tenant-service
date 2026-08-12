import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import {
  customerDirectPaymentsSchema,
  customerHandoverMutationSchema,
  customerHandoverSchema,
  customerPaymentDecisionSchema,
} from "../contracts/customerClosure";

export async function getCustomerHandover(jobId: string) {
  const response = await authenticatedRequest({ method: "GET", path: `/v1/customer/service-jobs/${jobId}/handover` });
  return parseApiSuccess(response.json, customerHandoverSchema);
}

export async function acknowledgeCustomerHandover(jobId: string) {
  const response = await authenticatedRequest({ method: "POST", path: `/v1/customer/service-jobs/${jobId}/acknowledge-handover` });
  return parseApiSuccess(response.json, customerHandoverMutationSchema);
}

export async function listCustomerDirectPayments() {
  const response = await authenticatedRequest({ method: "GET", path: "/v1/customer/direct-payments" });
  return parseApiSuccess(response.json, customerDirectPaymentsSchema);
}

export async function confirmCustomerDirectPayment(paymentId: string) {
  const response = await authenticatedRequest({ method: "POST", path: `/v1/customer/direct-payments/${paymentId}/confirm` });
  return parseApiSuccess(response.json, customerPaymentDecisionSchema);
}

export async function reportCustomerDirectPaymentNotPaid(paymentId: string) {
  const response = await authenticatedRequest({
    method: "POST",
    path: `/v1/customer/direct-payments/${paymentId}/report-mismatch`,
    body: { action: "not_paid", note: "Customer reported that this direct payment was not made." },
  });
  return parseApiSuccess(response.json, customerPaymentDecisionSchema);
}
