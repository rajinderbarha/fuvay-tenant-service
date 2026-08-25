import { selectProblems, shuffleProblems } from "../problemSelection";
import { HomeQuickIssue } from "../customerHome";
import { asCategoryId } from "../ids";

function issue(n: number, slug: string | null = "air-conditioning"): HomeQuickIssue {
  return {
    issueId: `i-${n}`,
    label: `Problem ${n}`,
    categoryId: asCategoryId("cat-1"),
    categorySlug: slug,
    categoryName: "Air Conditioning",
    intent: "repair" as const,
  };
}

const TWENTY = Array.from({ length: 20 }, (_, i) => issue(i + 1));

describe("selectProblems", () => {
  it("fills both sections without repeating a problem", () => {
    const { tiles, circles } = selectProblems(TWENTY, 8, 12);
    expect(tiles).toHaveLength(8);
    expect(circles).toHaveLength(12);
    const ids = new Set([...tiles, ...circles].map(i => i.issueId));
    expect(ids.size).toBe(20);
  });

  it("is stable for the same payload, so tiles do not move under a finger", () => {
    // Reshuffling per render would move a tile mid-tap and make the screen twitch
    // on any unrelated state change.
    const a = selectProblems(TWENTY, 8, 12);
    const b = selectProblems(TWENTY, 8, 12);
    expect(a.tiles.map(i => i.issueId)).toEqual(b.tiles.map(i => i.issueId));
    expect(a.circles.map(i => i.issueId)).toEqual(b.circles.map(i => i.issueId));
  });

  it("does not simply take them in payload order", () => {
    // Otherwise "random" would be a claim the code does not keep.
    const { tiles } = selectProblems(TWENTY, 8, 12);
    expect(tiles.map(i => i.issueId)).not.toEqual(TWENTY.slice(0, 8).map(i => i.issueId));
  });

  it("reshuffles when the list itself changes", () => {
    const fewer = selectProblems(TWENTY.slice(0, 19), 8, 12);
    const all = selectProblems(TWENTY, 8, 12);
    expect(fewer.tiles.map(i => i.issueId)).not.toEqual(all.tiles.map(i => i.issueId));
  });

  it("wraps round rather than rendering a half-empty section", () => {
    // Ten problems cannot fill 8 + 12 distinctly. A repeat further down the
    // screen costs less than a section that looks broken.
    const ten = TWENTY.slice(0, 10);
    const { tiles, circles } = selectProblems(ten, 8, 12);
    expect(tiles).toHaveLength(8);
    expect(circles).toHaveLength(10);
  });

  it("never offers a problem that cannot open the assistant", () => {
    const withBroken = [...TWENTY.slice(0, 9), issue(99, null)];
    const { tiles, circles } = selectProblems(withBroken, 8, 12);
    for (const picked of [...tiles, ...circles]) {
      expect(picked.categorySlug).toBeTruthy();
    }
  });

  it("returns empty sections for an empty list", () => {
    expect(selectProblems([], 8, 12)).toEqual({ tiles: [], circles: [] });
  });

  it("keeps every problem when shuffling", () => {
    const shuffled = shuffleProblems(TWENTY);
    expect(shuffled).toHaveLength(TWENTY.length);
    expect(new Set(shuffled.map(i => i.issueId)).size).toBe(TWENTY.length);
  });
});
