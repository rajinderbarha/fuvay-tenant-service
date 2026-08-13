"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function LegacyTopupsRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace(`/admin/home-services/finance?tab=credits&credits_tab=topups`);
  }, [router]);
  return null;
}
