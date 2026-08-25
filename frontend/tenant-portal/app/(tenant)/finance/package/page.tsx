import { redirect } from "next/navigation";

// Left pointing at /packages deliberately: unlike its three siblings, this
// route IS about package selection and purchase, which is the one thing
// /packages owns that the Home Services Finance Hub does not.
export default function FinancePackagePage() {
  redirect("/packages");
}
