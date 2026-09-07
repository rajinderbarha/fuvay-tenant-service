"use client";

import React, {
  forwardRef, useEffect, useImperativeHandle, useMemo, useState,
} from "react";

export interface InlinePriceType {
  id: string;
  name: string;
  price: number | null;
  enabled?: boolean;
  brandCoverage?: { mode: "all" | "selected"; brand_ids: string[] } | null;
}

export interface InlinePriceBrand {
  id: string;
  name: string;
  canOverride?: boolean;
  enabled?: boolean;
}

export interface InlineBrandException {
  key: string;
  typeId?: string;
  brandId: string;
  price: number | null;
  persisted: boolean;
}

export interface InlineDimensionPricingEditorHandle {
  save: () => Promise<void>;
}

interface Props {
  basePrice: number | null;
  types: InlinePriceType[];
  brands: InlinePriceBrand[];
  exceptions: InlineBrandException[];
  loading?: boolean;
  onSaveTypes?: (typeIds: string[], brandCoverageByType: Record<string, { mode: "all" | "selected"; brand_ids: string[] }>) => Promise<unknown>;
  onSaveBrands?: (brandIds: string[]) => Promise<unknown>;
  onSaveType: (typeId: string, price: number) => Promise<unknown>;
  onClearType: (typeId: string) => Promise<unknown>;
  onClearTypePrices: () => Promise<unknown>;
  onSaveBrand: (typeId: string | undefined, brandId: string, price: number) => Promise<unknown>;
  onClearBrand: (typeId: string | undefined, brandId: string) => Promise<unknown>;
  onDirtyChange?: (dirty: boolean) => void;
}

type BrandMode = "all" | "specific";

function positiveNumber(value: string | undefined) {
  const parsed = Number(value);
  return value?.trim() && Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

export const InlineDimensionPricingEditor = forwardRef<InlineDimensionPricingEditorHandle, Props>(
  function InlineDimensionPricingEditor({
    basePrice, types, brands, exceptions, loading = false,
    onSaveTypes, onSaveBrands, onSaveType, onClearType, onClearTypePrices,
    onSaveBrand, onClearBrand, onDirtyChange,
  }, ref) {
    const [varyByType, setVaryByType] = useState(false);
    const [activeTypeIds, setActiveTypeIds] = useState<string[]>([]);
    const [typeValues, setTypeValues] = useState<Record<string, string>>({});
    const [brandModes, setBrandModes] = useState<Record<string, BrandMode>>({});
    const [selectedBrands, setSelectedBrands] = useState<Record<string, string[]>>({});
    const [brandValues, setBrandValues] = useState<Record<string, string>>({});
    const [dirty, setDirty] = useState(false);
    const [saving, setSaving] = useState(false);

    const initialKey = useMemo(() => JSON.stringify({ basePrice, types, brands, exceptions }), [basePrice, types, brands, exceptions]);
    useEffect(() => {
      // Individual save requests refresh props while the remaining requests
      // are still running. Never overwrite the user's in-flight selection.
      if (dirty || saving) return;
      const enabledTypeIds = types.filter(type => type.enabled !== false).map(type => type.id);
      const pricedTypeIds = types.filter(type => type.price != null).map(type => type.id);
      const initialModes: Record<string, BrandMode> = {};
      const initialBrands: Record<string, string[]> = {};
      const initialBrandValues: Record<string, string> = {};
      const enabledBrands = brands.filter(brand => brand.enabled !== false).map(brand => brand.id);
      const hasSavedSubset = enabledBrands.length > 0 && enabledBrands.length < brands.length;
      for (const type of types) {
        const typeExceptions = exceptions.filter(row => row.typeId === type.id);
        initialModes[type.id] = type.brandCoverage
          ? type.brandCoverage.mode === "selected" ? "specific" : "all"
          : hasSavedSubset ? "specific" : "all";
        initialBrands[type.id] = type.brandCoverage
          ? type.brandCoverage.brand_ids.filter(id => brands.some(brand => brand.id === id))
          : hasSavedSubset ? enabledBrands : [];
        typeExceptions.forEach(row => { initialBrandValues[`${type.id}:${row.brandId}`] = String(row.price ?? ""); });
      }
      setVaryByType(pricedTypeIds.length > 0);
      setActiveTypeIds(enabledTypeIds.length ? enabledTypeIds : types.slice(0, 1).map(type => type.id));
      setTypeValues(Object.fromEntries(types.map(type => [type.id, String(type.price ?? "")])));
      setBrandModes(initialModes);
      setSelectedBrands(initialBrands);
      setBrandValues(initialBrandValues);
      setDirty(false);
    // The serialized server snapshot is the reset boundary. Local clicks do not alter it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [initialKey, dirty, saving]);

    useEffect(() => { onDirtyChange?.(dirty); }, [dirty, onDirtyChange]);

    const eligibleBrands = brands; // Matching support does not depend on permission to override price.
    const activeTypes = types.filter(type => activeTypeIds.includes(type.id));

    function change(mutator: () => void) {
      mutator();
      setDirty(true);
    }

    function toggleType(typeId: string) {
      change(() => setActiveTypeIds(current => {
        if (!current.includes(typeId)) return [...current, typeId];
        return current.length === 1 ? current : current.filter(id => id !== typeId);
      }));
    }

    function setMode(typeId: string, mode: BrandMode) {
      change(() => setBrandModes(current => ({ ...current, [typeId]: mode })));
    }

    function toggleBrand(typeId: string, brandId: string) {
      change(() => setSelectedBrands(current => {
        const selected = current[typeId] ?? [];
        return {
          ...current,
          [typeId]: selected.includes(brandId)
            ? selected.filter(id => id !== brandId)
            : [...selected, brandId],
        };
      }));
    }

    useImperativeHandle(ref, () => ({
      save: async () => {
        if (loading || saving) throw new Error("Wait for service choices to finish loading or saving.");
        const everyBrandId = brands.map(brand => brand.id);
        const savedBrandIds = brands.filter(brand => brand.enabled !== false).map(brand => brand.id);
        const usesAllBrands = activeTypeIds.some(typeId => (brandModes[typeId] ?? "all") === "all");
        const coverage = Object.fromEntries(activeTypeIds.map(typeId => [typeId, {
          mode: (brandModes[typeId] ?? "all") === "all" ? "all" as const : "selected" as const,
          brand_ids: (brandModes[typeId] ?? "all") === "all" ? [] : (selectedBrands[typeId] ?? []),
        }]));
        const desiredBrandIds = !types.length
          ? (savedBrandIds.length ? savedBrandIds : everyBrandId)
          : usesAllBrands
          ? everyBrandId
          : Array.from(new Set(activeTypeIds.flatMap(typeId => selectedBrands[typeId] ?? [])));
        // The default visible "All brands" is a selection too. Persist it
        // on Save even if the user only edited the service's base price.
        const matchingChanged = (brands.length > 0 && activeTypes.some(type => JSON.stringify(type.brandCoverage) !== JSON.stringify(coverage[type.id])))
          || desiredBrandIds.length !== savedBrandIds.length
          || desiredBrandIds.some(id => !savedBrandIds.includes(id))
          || activeTypeIds.some(id => !types.some(type => type.id === id && type.enabled !== false));
        if (!dirty && !matchingChanged) return;
        if (brands.length) {
          const empty = activeTypes.find(type => brandModes[type.id] === "specific" && !(selectedBrands[type.id]?.length));
          if (empty) throw new Error(`Select at least one supported brand for ${empty.name}, or choose All brands.`);
        }
        setSaving(true);
        try {
          if (onSaveTypes) await onSaveTypes(activeTypeIds, brands.length ? coverage : {});
          if (onSaveBrands) await onSaveBrands(desiredBrandIds);
          if (!dirty) return; // Matching repair must not clear saved prices.

          if (!varyByType) {
            await onClearTypePrices();
            await Promise.all(exceptions.map(row => onClearBrand(row.typeId, row.brandId)));
            setDirty(false);
            return;
          }

          for (const type of activeTypes) {
            const nextPrice = positiveNumber(typeValues[type.id]);
            if (nextPrice == null && type.price != null) await onClearType(type.id);
            else if (nextPrice != null && nextPrice !== type.price) await onSaveType(type.id, nextPrice);
          }

          const desiredExceptionKeys = new Set<string>();
          for (const typeId of activeTypeIds) {
            if ((brandModes[typeId] ?? "all") !== "specific") continue;
            for (const brandId of selectedBrands[typeId] ?? []) {
              const key = `${typeId}:${brandId}`;
              desiredExceptionKeys.add(key);
              const nextPrice = positiveNumber(brandValues[key]);
              const existing = exceptions.find(row => row.typeId === typeId && row.brandId === brandId);
              if (nextPrice != null && nextPrice !== existing?.price) await onSaveBrand(typeId, brandId, nextPrice);
            }
          }
          for (const existing of exceptions) {
            const key = `${existing.typeId ?? "default"}:${existing.brandId}`;
            if (!desiredExceptionKeys.has(key)) await onClearBrand(existing.typeId, existing.brandId);
          }
          setDirty(false);
        } finally {
          setSaving(false);
        }
      },
    }), [
      dirty, loading, saving, types, activeTypeIds, activeTypes, varyByType, brandModes, selectedBrands,
      typeValues, brandValues, brands, exceptions, onSaveTypes, onSaveBrands,
      onSaveType, onClearType, onClearTypePrices, onSaveBrand, onClearBrand,
    ]);

    return (
      <div className="pricing-dimension-editor" aria-busy={loading || saving}>
        {types.length > 0 && (
          <>
            <div className="pricing-type-toggle-row">
              <span>
                <strong>Price differs by type</strong>
                <small>{varyByType ? `Blank types fall back to ₹${basePrice?.toLocaleString("en-IN") ?? "—"}` : `All ${types.length} types use ₹${basePrice?.toLocaleString("en-IN") ?? "—"}`}</small>
              </span>
              <button type="button" role="switch" aria-checked={varyByType} aria-label="Price differs by type" className="pricing-switch" disabled={loading || saving}
                onClick={() => change(() => setVaryByType(value => !value))}><span /></button>
            </div>

            {(
              <>
                <div className="pricing-dimension-choice-block">
                  <p>Which types do you actually service? Unselected types stay hidden from customers.</p>
                  <div className="pricing-choice-chips">
                    {types.map(type => (
                      <button key={type.id} type="button" aria-pressed={activeTypeIds.includes(type.id)} disabled={loading || saving}
                        onClick={() => toggleType(type.id)}>{type.name}</button>
                    ))}
                  </div>
                </div>

                <div className="pricing-type-card-list">
                  {activeTypes.map(type => {
                    const mode = brandModes[type.id] ?? "all";
                    const selected = selectedBrands[type.id] ?? [];
                    const inheritedPrice = positiveNumber(typeValues[type.id]) ?? basePrice;
                    return (
                      <section className="pricing-type-card" key={type.id}>
                        <div className="pricing-type-card-head">
                          <strong>{type.name}</strong>
                          {varyByType && <span className="pricing-compact-money"><span>₹</span><input aria-label={`${type.name} price`} type="number" min={1}
                            value={typeValues[type.id] ?? ""} disabled={saving}
                            onChange={event => change(() => setTypeValues(current => ({ ...current, [type.id]: event.target.value })))}
                            placeholder={basePrice != null ? String(basePrice) : "—"} /></span>}
                        </div>

                        {brands.length > 0 && (
                          <>
                            <div className="pricing-brand-mode" aria-label={`Brand coverage for ${type.name}`}>
                              <button type="button" aria-pressed={mode === "all"} onClick={() => setMode(type.id, "all")}>All brands</button>
                              <button type="button" aria-pressed={mode === "specific"} onClick={() => setMode(type.id, "specific")}>Specific brands</button>
                            </div>
                            <p className="pricing-type-brand-hint">
                              {mode === "all"
                                ? `Every brand of ${type.name} pays ₹${inheritedPrice?.toLocaleString("en-IN") ?? "—"}.`
                                : `Pick the brands of ${type.name} you actually service. Prices inherit unless overridden.`}
                            </p>
                            {mode === "specific" && (
                              <>
                                <div className="pricing-choice-chips is-compact">
                                  {eligibleBrands.map(brand => (
                                    <button key={brand.id} type="button" aria-pressed={selected.includes(brand.id)} disabled={saving}
                                      onClick={() => toggleBrand(type.id, brand.id)}>{brand.name}</button>
                                  ))}
                                </div>
                                {varyByType && selected.length > 0 && (
                                  <div className="pricing-brand-price-list">
                                    {selected.map(brandId => {
                                      const brand = eligibleBrands.find(candidate => candidate.id === brandId);
                                      if (!brand) return null;
                                      const key = `${type.id}:${brandId}`;
                                      return (
                                        <label className="pricing-compact-price-row" key={brandId}>
                                          <span>{brand.name}</span>
                                          <span className="pricing-compact-money"><span>₹</span><input aria-label={`${type.name} ${brand.name} price`} type="number" min={1}
                                            value={brandValues[key] ?? ""} disabled={saving || brand.canOverride === false}
                                            onChange={event => change(() => setBrandValues(current => ({ ...current, [key]: event.target.value })))}
                                            placeholder={inheritedPrice != null ? String(inheritedPrice) : "—"} /></span>
                                        </label>
                                      );
                                    })}
                                  </div>
                                )}
                              </>
                            )}
                          </>
                        )}
                      </section>
                    );
                  })}
                </div>
              </>
            )}
          </>
        )}
        {dirty && <p className="pricing-unsaved-note" role="status">Unsaved changes — use the action bar below when you are ready.</p>}
      </div>
    );
  },
);
