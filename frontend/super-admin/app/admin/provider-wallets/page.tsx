import { redirect } from "next/navigation";

export default function RetiredProviderWalletsRoute() {
  redirect(`/admin/home-services/finance?tab=credits&credits_tab=accounts`);
}
