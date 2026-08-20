import { redirect } from "next/navigation";

export default function RetiredCompletedJobDeductionRoute() {
  redirect("/admin/home-services/finance?tab=provider-charges");
}
