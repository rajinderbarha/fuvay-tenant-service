"use client";

import React, { useId, useState } from "react";

export interface TooltipProps {
  label: string;
  children: React.ReactElement<{ "aria-describedby"?: string }>;
  side?: "top" | "bottom";
}

export function Tooltip({ label, children, side = "top" }: TooltipProps) {
  const [visible, setVisible] = useState(false);
  const id = useId();

  return (
    <span
      style={{ position: "relative", display: "inline-flex" }}
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onFocus={() => setVisible(true)}
      onBlur={() => setVisible(false)}
    >
      {React.cloneElement(children, { "aria-describedby": id })}
      {visible && (
        <span
          role="tooltip"
          id={id}
          style={{
            position: "absolute",
            [side === "top" ? "bottom" : "top"]: "calc(100% + 0.375rem)",
            left: "50%",
            transform: "translateX(-50%)",
            background: "var(--text-primary)",
            color: "var(--bg)",
            padding: "0.25rem 0.5rem",
            borderRadius: "var(--radius-sm)",
            fontSize: "0.6875rem",
            whiteSpace: "nowrap",
            zIndex: 1200,
            boxShadow: "var(--shadow-md)",
          }}
        >
          {label}
        </span>
      )}
    </span>
  );
}
