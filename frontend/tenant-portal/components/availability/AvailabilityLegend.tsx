"use client";
/** Legend for the weekly grid. The swatches deliberately reuse the SAME
 *  .avail-cell tone classes the grid cells use, inside a .avail-grid scope, so
 *  the two can never drift: a colour change in one is a colour change in both.
 *  A hand-matched legend is how a board ends up claiming grey means "break"
 *  while the grid is drawing it for time off. */
import React from "react";
import { GRID_TONES } from "./WeeklyGrid";

function Swatch({ tone, label }: { tone: string; label: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 11.5, color: "var(--text-secondary)" }}>
      <span className={`avail-cell ${tone}`} style={{ width: 13, height: 13, padding: 0, borderRadius: 4, flexShrink: 0 }}/>
      {label}
    </div>
  );
}

export function AvailabilityLegend({ timezone, breakLabel }: {
  timezone?: string | null;
  breakLabel?: string | null;
}) {
  return (
    <div className="avail-grid" style={{ marginTop: 16, padding: "0 4px" }}>
      {/* Included here too: the legend renders even when the grid does not (empty
          roster, loading), and without the tones its swatches would be blank boxes. */}
      <style>{GRID_TONES}</style>
      <div style={{ display: "flex", gap: 18, flexWrap: "wrap", alignItems: "center" }}>
        <Swatch tone="avail-ok" label="Available"/>
        <Swatch tone="avail-as" label="Assigned"/>
        {/* Break and time off share a tone because they are the same thing to a
            dispatcher looking for a slot -- not workable. The label carries the
            distinction rather than a colour nobody could tell apart anyway. */}
        <Swatch tone="avail-mu" label={breakLabel ? `Break (${breakLabel})` : "Break"}/>
        <Swatch tone="avail-mu" label="Time off"/>
        <Swatch tone="avail-ov" label="Date override"/>
        <Swatch tone="avail-cf" label="Conflict"/>
      </div>
      {timezone && (
        <p style={{ fontSize: 11.5, color: "var(--text-tertiary)", margin: "10px 0 0", fontStyle: "italic" }}>
          All times shown in {timezone}
        </p>
      )}
    </div>
  );
}
