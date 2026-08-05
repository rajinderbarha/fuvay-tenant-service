"use client";
import { useParams } from "next/navigation";
import { useCallback } from "react";
import { VerticalComplaintWorkspace } from "../../../../components/directory/VerticalComplaintWorkspace";
import { verticalCatalogApi } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";

export default function VerticalComplaintsPage() {
  const params = useParams();
  const vertical = String(params.vertical);
  const vApi = useApi(useCallback(() => verticalCatalogApi.getVertical(vertical.replace(/-/g, "_")), [vertical]));
  const label = (vApi.data as { label?: string } | null)?.label ?? vertical;
  return <VerticalComplaintWorkspace vertical={vertical} verticalLabel={label}/>;
}
