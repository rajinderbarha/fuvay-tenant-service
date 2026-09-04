"use client";

import React from "react";

interface RepairEstimateGuidanceEditorProps {
  enabled: boolean;
  minimum: string;
  maximum: string;
  disabled?: boolean;
  onEnabledChange: (enabled: boolean) => void;
  onMinimumChange: (value: string) => void;
  onMaximumChange: (value: string) => void;
}

/**
 * Optional customer-facing guidance for inspection jobs. This is deliberately
 * separate from the visit fee: the range is informational and never becomes a
 * fixed repair quote before diagnosis.
 */
export function RepairEstimateGuidanceEditor({
  enabled,
  minimum,
  maximum,
  disabled = false,
  onEnabledChange,
  onMinimumChange,
  onMaximumChange,
}: RepairEstimateGuidanceEditorProps) {
  return (
    <div className="pricing-estimate-guidance">
      <button
        type="button"
        role="switch"
        aria-checked={enabled}
        className="pricing-type-toggle-row pricing-estimate-toggle"
        disabled={disabled}
        onClick={() => onEnabledChange(!enabled)}
      >
        <span>
          <strong>Show customers a rough range</strong>
          <small>Guidance only — the real amount is your estimate after diagnosis.</small>
        </span>
        <span className="pricing-switch" aria-hidden="true"><span /></span>
      </button>

      {enabled && (
        <div className="pricing-estimate-range" aria-label="Repair estimate guidance range">
          <p>Set the general range customers see before booking an inspection.</p>
          <div className="pricing-estimate-range-row">
            <span>All types</span>
            <label className="pricing-compact-money">
              <span>₹</span>
              <input
                aria-label="Minimum rough repair estimate"
                type="number"
                min={1}
                value={minimum}
                disabled={disabled}
                onChange={event => onMinimumChange(event.target.value)}
                placeholder="1200"
              />
            </label>
            <span className="pricing-range-separator">–</span>
            <label className="pricing-compact-money">
              <span>₹</span>
              <input
                aria-label="Maximum rough repair estimate"
                type="number"
                min={1}
                value={maximum}
                disabled={disabled}
                onChange={event => onMaximumChange(event.target.value)}
                placeholder="2500"
              />
            </label>
          </div>
        </div>
      )}
    </div>
  );
}
