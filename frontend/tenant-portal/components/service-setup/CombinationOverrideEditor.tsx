"use client";
import React, { useCallback, useEffect, useState } from "react";
import { useApi, useAction } from "../../hooks/useApi";
import { serviceSetupApi, type PriceResolution } from "../../lib/api";
import { DataTable, Badge, Skeleton } from "../shared/ui";
import { PriceRangeField } from "./PriceRangeField";

/** Spec section 13: exact-combination pricing overview. Shows every Type x
 * Brand combination this service could have, whether it's currently
 * supported, and its resolved price -- all from the real backend resolver,
 * never computed client-side. Lets a tenant configure prices for specific
 * combinations without ever requiring a tenant default (exact-only pricing). */
export function CombinationOverrideEditor({ tenantServiceId }: { tenantServiceId: string }) {
  const typesRes = useApi(useCallback(() => serviceSetupApi.getTypes(tenantServiceId), [tenantServiceId]));
  const brandsRes = useApi(useCallback(() => serviceSetupApi.getBrands(tenantServiceId), [tenantServiceId]));

  const types = typesRes.data?.types ?? [];
  const brands = brandsRes.data?.brands ?? [];

  const [resolutions, setResolutions] = useState<Record<string, PriceResolution>>({});
  const [loadingGrid, setLoadingGrid] = useState(false);

  useEffect(() => {
    if (types.length === 0 || brands.length === 0) return;
    let cancelled = false;
    setLoadingGrid(true);
    Promise.all(
      types.flatMap(t => brands.map(async b => {
        const key = `${t.service_type_id}:${b.brand_id}`;
        try {
          const r = await serviceSetupApi.resolvePrice(tenantServiceId, t.service_type_id, b.brand_id);
          return [key, r] as const;
        } catch {
          return [key, { resolved: false, reason: "NO_TENANT_PRICE_FOR_COMBINATION" } as PriceResolution] as const;
        }
      })),
    ).then(entries => {
      if (cancelled) return;
      setResolutions(Object.fromEntries(entries));
      setLoadingGrid(false);
    });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantServiceId, types.length, brands.length]);

  const overrideAction = useAction(useCallback(
    (typeId: string, brandId: string, min: number, max: number) =>
      serviceSetupApi.setBrandPricing(tenantServiceId, brandId, min, max, typeId),
    [tenantServiceId]));

  async function refreshOne(typeId: string, brandId: string, min: number, max: number) {
    await overrideAction.execute(typeId, brandId, min, max);
    const r = await serviceSetupApi.resolvePrice(tenantServiceId, typeId, brandId);
    setResolutions(prev => ({ ...prev, [`${typeId}:${brandId}`]: r }));
  }

  if (types.length === 0 || brands.length === 0) return null;

  const rows = types.flatMap(t => brands.map(b => ({
    key: `${t.service_type_id}:${b.brand_id}`,
    typeId: t.service_type_id, brandId: b.brand_id,
    typeName: t.name, brandName: b.name,
  })));

  return (
    <div>
      <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 4px" }}>All combinations</h3>
      <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 10px" }}>
        A full overview of every type + brand combination. You can price an exact combination directly here
        without needing a default price for the type or the service.
      </p>
      {typesRes.loading || brandsRes.loading || loadingGrid ? <Skeleton height={160} /> : (
        <DataTable
          columns={[
            { key: "typeName", label: "Type" },
            { key: "brandName", label: "Brand" },
            {
              key: "supported", label: "Supported",
              render: (_v, row) => {
                const res = resolutions[(row as { key: string }).key];
                return res?.resolved ? <Badge variant="success" size="sm">Yes</Badge>
                  : res?.reason === "COMBINATION_NOT_SUPPORTED"
                  ? <Badge variant="muted" size="sm">No</Badge>
                  : <Badge variant="warning" size="sm">Unpriced</Badge>;
              },
            },
            {
              key: "price", label: "Price",
              render: (_v, row) => {
                const r = row as { key: string; typeId: string; brandId: string };
                const res = resolutions[r.key];
                if (res?.resolved) {
                  return (
                    <PriceRangeField label="" min={res.minimum_price ?? null} max={res.maximum_price ?? null}
                      onSave={(min, max) => refreshOne(r.typeId, r.brandId, min, max)}
                      saving={overrideAction.loading} />
                  );
                }
                if (res?.reason === "COMBINATION_NOT_SUPPORTED") return <span style={{ color: "var(--text-tertiary)" }}>—</span>;
                return (
                  <PriceRangeField label="" min={null} max={null}
                    onSave={(min, max) => refreshOne(r.typeId, r.brandId, min, max)}
                    saving={overrideAction.loading} />
                );
              },
            },
          ]}
          rows={rows as unknown as Record<string, unknown>[]}
          emptyText="No combinations available."
        />
      )}
    </div>
  );
}
