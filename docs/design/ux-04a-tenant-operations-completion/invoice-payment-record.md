# Invoice / On-Site Payment Record (UX-04A)

New: `components/ux04/InvoicePaymentSummary.tsx`, wired into Job Detail
Workspace. Language deliberately chosen: "on-site payment record"
(labelled from `invoice.paymentMethodRecord`), "payment recorded" (state
label), never "processed by ServiceOS"; "commission deducted from tenant
credit" (from `invoice.commissionDeductionAmount`), never "payout". A
footer sentence explicitly states ServiceOS does not process this
on-site payment. No capture/refund/payout button exists in the component
— by construction there is no click handler that could carry one.
