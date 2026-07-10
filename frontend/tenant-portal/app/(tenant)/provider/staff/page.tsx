"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function StaffRedirectPage() {
  const router = useRouter();
  useEffect(() => { router.replace("/provider/team-members"); }, [router]);
  return null;
}
