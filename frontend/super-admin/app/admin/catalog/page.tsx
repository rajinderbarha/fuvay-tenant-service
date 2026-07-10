"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

// Catalog tabs have been promoted to standalone pages:
//   /admin/master-services  — Master Services
//   /admin/types-brands     — Types & Brands
//   /admin/pricing-rules    — Pricing Rules
//   /admin/categories       — Categories (was already standalone)
//   /admin/pricing-tiers    — Pricing Tiers (was already standalone)

export default function CatalogRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/admin/master-services");
  }, [router]);
  return null;
}
