/** Restrained, functional motion durations/easings. No decorative continuous
 * animation. Screens must check `useReducedMotion()` (design-system/themes)
 * before applying any of these. */
export const motion = {
  duration: {
    instant: 0,
    fast: 120,
    base: 200,
    slow: 320,
  },
  easing: {
    standard: "ease-in-out",
    decelerate: "ease-out",
    accelerate: "ease-in",
  },
} as const;
