import { redirect } from "next/navigation";

// Consolidated into /packages: that page now shows package selection,
// active-purchase renewal, instant credit top-up, AND the usage credit
// balance this page used to show on its own — one screen instead of two
// different views of the same account under "Package & Credits" vs "Billing".
export default function FinancePackagePage() {
  redirect("/packages");
}
