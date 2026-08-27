import { redirect } from "next/navigation";

// This route previously rendered a legacy Wallet/Payouts page (Razorpay
// top-up, "Request Payout" with bank account fields) that predates the
// Home Services Usage Credit model and violates the platform's "customer
// pays provider directly, no platform wallet/payout" business rules.
//
// It then redirected to /packages. Corrected to the Home Services Finance
// Hub: /packages is the package SELECTION/purchase surface, while the Hub is
// what the sidebar's "Finance & Credits" item points at and is the canonical
// home for the usage-credit wallet, technician seats, financial activity,
// published policy and commission rates. Sending a finance-named route to a
// page the sidebar never links left two competing "finance" destinations.
export default function FinancePage() {
  redirect("/home-services/finance");
}
