"use client";
import { useParams } from "next/navigation";
import { useCallback } from "react";
import { VerticalProviderDirectory } from "../../../../components/directory/VerticalProviderDirectory";
import { verticalCatalogApi } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";

// VERTICAL-DIRECTORY-FRAMEWORK: ONE page serves every Business Vertical --
// `vertical` is a Next.js dynamic route param (the URL, e.g.
// "home-services"), never a client-controlled security boundary: the
// backend independently re-resolves and validates it on every request.
export default function VerticalProvidersPage() {
  const params = useParams();
  const vertical = String(params.vertical);
  const vApi = useApi(useCallback(() => verticalCatalogApi.getVertical(vertical.replace(/-/g, "_")), [vertical]));
  const label = (vApi.data as { label?: string } | null)?.label ?? vertical;
  return <VerticalProviderDirectory vertical={vertical} verticalLabel={label}/>;
}
