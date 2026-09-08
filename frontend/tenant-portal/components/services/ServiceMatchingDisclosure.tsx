"use client";

import React, { useState } from "react";

/** Matching remains independent of optional customer pricing. */
export function ServiceMatchingDisclosure({ children, expandedByPricing = false }: {
  children: React.ReactNode;
  expandedByPricing?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  if (expandedByPricing) return <>{children}</>;
  return (
    <section className="pricing-matching-section">
      <button type="button" className="pricing-type-toggle-row pricing-matching-toggle"
        aria-expanded={expanded} onClick={() => setExpanded(value => !value)}>
        <span>
          <strong>Supported types & brands</strong>
          <small>Choose which jobs you accept. These selections apply independently of pricing.</small>
        </span>
        <span aria-hidden="true">{expanded ? "−" : "+"}</span>
      </button>
      {expanded && <div className="pricing-matching-body">{children}</div>}
    </section>
  );
}
