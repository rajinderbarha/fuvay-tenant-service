export const duration = {
  instant: 0,
  fast: 120,
  standard: 200,
  slow: 320,
} as const;

export const easing = {
  entering: [0, 0, 0.2, 1] as [number, number, number, number],
  exiting: [0.4, 0, 1, 1] as [number, number, number, number],
  standard: [0.4, 0, 0.2, 1] as [number, number, number, number],
  emphasized: [0.2, 0, 0, 1] as [number, number, number, number],
};
