import { redirect } from "next/navigation";

export default function RetiredDataRequestDetailPage() {
  redirect("/provider/compliance?tab=my-requests");
}
