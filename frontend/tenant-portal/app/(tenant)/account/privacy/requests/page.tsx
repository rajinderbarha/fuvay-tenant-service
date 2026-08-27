import { redirect } from "next/navigation";

export default function RetiredDataRequestsPage() {
  redirect("/provider/compliance?tab=my-requests");
}
