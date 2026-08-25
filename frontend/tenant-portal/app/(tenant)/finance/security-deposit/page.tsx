import { redirect } from "next/navigation";

// Consolidated into the Home Services Finance Hub's "Security Deposit" tab —
// the surface the sidebar's "Finance & Credits" item points at, which holds
// the deposit balance, liability holds and the deposit refund-request
// workflow. Previously redirected to /packages, a page the sidebar never
// links, which left two competing finance destinations.
export default function SecurityDepositPage() {
  redirect("/home-services/finance?tab=security-deposit");
}
