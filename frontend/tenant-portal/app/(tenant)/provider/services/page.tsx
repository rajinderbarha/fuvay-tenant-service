"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function ServicesRedirectPage() {
  const router = useRouter();
  useEffect(() => { router.replace("/provider/offerings"); }, [router]);
  return null;
}
