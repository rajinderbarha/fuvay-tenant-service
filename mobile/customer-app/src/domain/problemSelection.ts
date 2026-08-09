import { HomeQuickIssue } from "./customerHome";

/**
 * Which problems each Home section shows.
 *
 * "Random" here means random ONCE PER PAYLOAD, not per render. Reshuffling on
 * every render would move a tile out from under a finger mid-tap and make the
 * screen twitch on any unrelated state change; it would also be untestable. The
 * order is derived from the problem ids themselves, so the same payload always
 * produces the same arrangement and a genuinely new list produces a new one.
 *
 * The two sections are drawn from ONE shuffle and then split, so a problem never
 * appears in both -- until the catalogue is too small to fill them separately, at
 * which point the second section wraps back round rather than rendering short.
 */

/** Deterministic hash of a string. Not cryptographic -- it only has to spread
 * ids evenly and give the same answer every time. */
function hash(value: string): number {
  let h = 2166136261;
  for (let i = 0; i < value.length; i += 1) {
    h ^= value.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

/** Stable shuffle: sorts by a hash of each id mixed with the list's own size, so
 * adding or removing a problem reshuffles rather than merely inserting. */
export function shuffleProblems(issues: readonly HomeQuickIssue[]): HomeQuickIssue[] {
  const salt = String(issues.length);
  return [...issues].sort(
    (a, b) => hash(a.issueId + salt) - hash(b.issueId + salt),
  );
}

export interface ProblemSelection {
  /** The square-tile shortlist near the top. */
  tiles: HomeQuickIssue[];
  /** The larger circular set further down. */
  circles: HomeQuickIssue[];
}

/**
 * Splits the bookable problems between the two sections.
 *
 * Only problems that can actually open the assistant are considered: one with no
 * category slug cannot be booked from here, so it is dropped rather than rendered
 * as a tile that does nothing.
 */
export function selectProblems(
  issues: readonly HomeQuickIssue[],
  tileCount: number,
  circleCount: number,
): ProblemSelection {
  const tappable = shuffleProblems(issues.filter(i => !!i.categorySlug));
  const tiles = tappable.slice(0, tileCount);
  const rest = tappable.slice(tileCount);

  if (rest.length >= circleCount) {
    return { tiles, circles: rest.slice(0, circleCount) };
  }
  // Not enough distinct problems left. Fill from the front rather than showing a
  // half-empty section -- a repeat further down the screen is a smaller cost
  // than a section that looks broken.
  const wrapped = [...rest];
  for (const issue of tappable) {
    if (wrapped.length >= circleCount) break;
    if (!wrapped.some(w => w.issueId === issue.issueId)) wrapped.push(issue);
  }
  return { tiles, circles: wrapped };
}
