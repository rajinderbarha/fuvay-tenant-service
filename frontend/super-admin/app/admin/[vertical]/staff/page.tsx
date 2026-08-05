"use client";
import { useParams } from "next/navigation";
import { useCallback } from "react";
import { VerticalStaffDirectory } from "../../../../components/directory/VerticalStaffDirectory";
import { verticalCatalogApi } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";

export default function VerticalStaffPage() {
  const params = useParams();
  const vertical = String(params.vertical);
  const vApi = useApi(useCallback(() => verticalCatalogApi.getVertical(vertical.replace(/-/g, "_")), [vertical]));
  const label = (vApi.data as { label?: string } | null)?.label ?? vertical;
  return <VerticalStaffDirectory vertical={vertical} verticalLabel={label}/>;
}
