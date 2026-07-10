import { redirect } from "next/navigation";

// E2E-11 fix: this route previously rendered a legacy Wallet/Payouts page
// (Razorpay top-up, "Request Payout" with bank account fields) that
// predates the Home Services Usage Credit model and violates the
// platform's "customer pays provider directly, no platform wallet/payout"
// business rules. The real, correct finance overview already lives at
// /finance/package (package + Usage Credit balance), with
// /finance/usage-credit-ledger and /finance/security-deposit alongside
// it — exactly what the sidebar nav already links to. Redirect here
// instead of maintaining two contradictory finance pages.
export default function FinancePage() {
  redirect("/finance/package");
}
