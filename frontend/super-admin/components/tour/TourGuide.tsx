"use client";

import React, { useEffect, useState } from "react";
import type { useTour } from "../../hooks/useTour";

type TourState = ReturnType<typeof useTour>;

export function TourGuide({ tour }: { tour: TourState }) {
  const { active, currentStep, step, totalSteps, next, prev, skip, isFirst, isLast } = tour;
  const [pos, setPos] = useState({ top: 100, left: 100, width: 0, height: 0 });

  useEffect(() => {
    if (!active || !currentStep) return;
    const element = document.getElementById(currentStep.targetId);
    if (!element) return;
    const rect = element.getBoundingClientRect();
    setPos({ top: rect.top, left: rect.left, width: rect.width, height: rect.height });
    element.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [active, currentStep, step]);

  if (!active || !currentStep) return null;

  const tooltipTop = currentStep.position === "bottom"
    ? pos.top + pos.height + 12
    : currentStep.position === "top"
      ? pos.top - 140
      : pos.top;
  const tooltipLeft = currentStep.position === "right"
    ? pos.left + pos.width + 14
    : currentStep.position === "left"
      ? pos.left - 300
      : pos.left;

  return (
    <>
      <div
        aria-hidden="true"
        style={{
          position: "fixed", inset: 0, zIndex: 498, background: "rgba(0,0,0,0.55)",
          backdropFilter: "blur(2px)", animation: "fadeIn 0.2s ease",
        }}
        onClick={skip}
      />
      <div
        aria-hidden="true"
        style={{
          position: "fixed", top: pos.top - 4, left: pos.left - 4,
          width: pos.width + 8, height: pos.height + 8, zIndex: 499,
          borderRadius: 12, boxShadow: "0 0 0 9999px rgba(0,0,0,0)",
          border: "2px solid var(--accent)", pointerEvents: "none",
          animation: "scaleIn 0.2s ease",
        }}
      />
      <section
        aria-label={`Admin tour step ${step + 1} of ${totalSteps}`}
        style={{
          position: "fixed", top: tooltipTop,
          left: Math.max(16, Math.min(tooltipLeft, window.innerWidth - 316)),
          width: 300, zIndex: 500, animation: "slideUp 0.2s cubic-bezier(0.34,1.56,0.64,1)",
        }}
      >
        <div style={{
          background: "var(--surface-elevated)", borderRadius: 14, padding: 20,
          boxShadow: "var(--shadow-lg)", border: "1px solid var(--border)",
        }}>
          <div aria-hidden="true" style={{ display: "flex", gap: 5, marginBottom: 14 }}>
            {Array.from({ length: totalSteps }).map((_, index) => (
              <div key={index} style={{
                height: 4, flex: 1, borderRadius: 999,
                background: index <= step ? "var(--accent)" : "var(--border)",
                transition: "background 0.2s",
              }} />
            ))}
          </div>
          <p style={{
            fontSize: 11, fontWeight: 700, color: "var(--accent)", margin: "0 0 6px",
            letterSpacing: "0.06em", textTransform: "uppercase",
          }}>
            Step {step + 1} of {totalSteps}
          </p>
          <h3 style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 8px" }}>
            {currentStep.title}
          </h3>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 18px", lineHeight: 1.5 }}>
            {currentStep.description}
          </p>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <button onClick={skip} style={{
              background: "none", border: "none", cursor: "pointer", fontSize: 12,
              color: "var(--text-tertiary)", fontFamily: "inherit",
            }}>
              Skip tour
            </button>
            <div style={{ display: "flex", gap: 8 }}>
              {!isFirst && (
                <button onClick={prev} style={{
                  padding: "7px 14px", borderRadius: 9, border: "1px solid var(--border)",
                  background: "var(--surface)", color: "var(--text-secondary)", fontSize: 12,
                  cursor: "pointer", fontFamily: "inherit", fontWeight: 500,
                }}>
                  Back
                </button>
              )}
              <button onClick={next} style={{
                padding: "7px 18px", borderRadius: 9, border: "none",
                background: "var(--brand)", color: "white", fontSize: 12,
                cursor: "pointer", fontFamily: "inherit", fontWeight: 600,
              }}>
                {isLast ? "Done ✓" : "Next →"}
              </button>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
