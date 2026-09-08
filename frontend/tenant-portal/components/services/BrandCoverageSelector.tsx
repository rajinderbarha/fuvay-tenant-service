"use client";

import React, { useState } from "react";

interface Props {
  brands: { brand_id: string; name: string; is_enabled: boolean }[];
  disabled?: boolean;
  onChange: (brandIds: string[]) => Promise<unknown>;
}

export function BrandCoverageSelector({ brands, disabled = false, onChange }: Props) {
  const [chooseSpecific, setChooseSpecific] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const allSelected = brands.length > 0 && brands.every(brand => brand.is_enabled);
  const specific = chooseSpecific || !allSelected;

  async function save(ids: string[], all = false) {
    if (saving || disabled) return;
    setSaving(true);
    setError("");
    try {
      await onChange(ids);
      if (all) setChooseSpecific(false);
    } catch (value) {
      setError(value instanceof Error ? value.message : "Could not save supported brands. Please retry.");
    } finally {
      setSaving(false);
    }
  }

  if (!brands.length) return <p>No brands are mapped yet. Ask an administrator to complete this service.</p>;

  return (
    <div className="pricing-dimension-choice-block is-brands">
      <div className="pricing-brand-mode" aria-label="Supported brand selection">
        <button type="button" aria-pressed={!specific} disabled={disabled || saving}
          onClick={() => save(brands.map(brand => brand.brand_id), true)}>All brands</button>
        <button type="button" aria-pressed={specific} disabled={disabled || saving}
          onClick={() => setChooseSpecific(true)}>Specific brands</button>
      </div>
      <p>{specific ? "Select the brands you service. Unselected brands stay hidden from customers." : "You service every brand currently configured for this service."}</p>
      {specific && <div className="pricing-choice-chips">
        {brands.map(brand => <button key={brand.brand_id} type="button" aria-pressed={brand.is_enabled}
          disabled={disabled || saving} onClick={() => save(brands.filter(candidate =>
            candidate.brand_id === brand.brand_id ? !brand.is_enabled : candidate.is_enabled,
          ).map(candidate => candidate.brand_id))}>{brand.name}</button>)}
      </div>}
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
