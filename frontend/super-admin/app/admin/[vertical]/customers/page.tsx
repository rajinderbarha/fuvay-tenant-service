"use client";
import { useParams } from "next/navigation";
import { useCallback } from "react";
import { VerticalCustomerDirectory } from "../../../../components/directory/VerticalCustomerDirectory";
import { verticalCatalogApi } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";

export default function VerticalCustomersPage() {
  const params = useParams();
  const vertical = String(params.vertical);
  const vApi = useApi(useCallback(() => verticalCatalogApi.getVertical(vertical.replace(/-/g, "_")), [vertical]));
  const label = (vApi.data as { label?: string } | null)?.label ?? vertical;
  return <VerticalCustomerDirectory vertical={vertical} verticalLabel={label}/>;
}
