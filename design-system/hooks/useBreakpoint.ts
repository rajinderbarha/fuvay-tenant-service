/** useBreakpoint — responsive breakpoint hook. */
import { useState, useEffect } from "react";
import { tokens } from "../tokens/tokens";

export type Breakpoint = "mobile" | "tablet" | "desktop" | "wide";

function getBreakpoint(width: number): Breakpoint {
  if (width >= tokens.breakpoints.wide)    return "wide";
  if (width >= tokens.breakpoints.desktop) return "desktop";
  if (width >= tokens.breakpoints.tablet)  return "tablet";
  return "mobile";
}

export function useBreakpoint() {
  const [bp, setBp] = useState<Breakpoint>("desktop");
  useEffect(() => {
    const update = () => setBp(getBreakpoint(window.innerWidth));
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);
  return {
    breakpoint: bp,
    isMobile:  bp === "mobile",
    isTablet:  bp === "tablet",
    isDesktop: bp === "desktop" || bp === "wide",
    isWide:    bp === "wide",
  };
}
