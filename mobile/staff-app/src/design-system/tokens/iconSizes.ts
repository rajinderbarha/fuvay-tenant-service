/** One icon library only: @expo/vector-icons (Ionicons set, for stroke-weight
 * consistency). Standard size scale -- section 13 of the foundation spec. */
export const iconSizes = {
  compact: 16,
  standard: 20,
  navigation: 24,
  feature: 32,
  emptyState: 40,
} as const;

export type IconSizeToken = keyof typeof iconSizes;
