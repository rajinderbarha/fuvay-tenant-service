import { redirect } from "next/navigation";

// This route previously rendered a legacy Wallet/Payouts page (Razorpay
// top-up, "Request Payout" with bank account fields) that predates the
// Home Services Usage Credit model and violates the platform's "customer
// pays provider directly, no platform wallet/payout" business rules.
// The real, correct finance overview now lives at /packages — package
// selection, renewal, credit top-up, usage credit ledger, and security
// deposit are all tabs on that one page. Redirect here instead of
// maintaining duplicate pages.
export default function FinancePage() {
  redirect("/packages");
}
