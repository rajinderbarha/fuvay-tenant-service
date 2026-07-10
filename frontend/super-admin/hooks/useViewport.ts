"use client";
import { useEffect, useState } from "react";

export type Viewport = "mobile" | "tablet" | "desktop";

function classify(width: number): Viewport {
  if (width < 768) return "mobile";
  if (width < 1200) return "tablet";
  return "desktop";
}

/** SSR-safe viewport breakpoint hook — defaults to "desktop" until mounted. */
export function useViewport(): Viewport {
  const [viewport, setViewport] = useState<Viewport>("desktop");

  useEffect(() => {
    const update = () => setViewport(classify(window.innerWidth));
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  return viewport;
}
