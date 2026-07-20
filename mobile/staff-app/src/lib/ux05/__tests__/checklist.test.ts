import { computeProgress, isItemComplete, missingRequiredItems, canComplete } from "../checklist";
import type { ChecklistExecutionView } from "../../../types/ux05";

function view(items: ChecklistExecutionView["sections"][0]["items"]): ChecklistExecutionView {
  return { meta: { readiness: "mock_design_only" }, jobId: "sj_1", sections: [{ title: "Safety", items }], progressPercent: 0, status: "in_progress" };
}

describe("isItemComplete", () => {
  it("treats a photo item complete only when photoAttached is true", () => {
    expect(isItemComplete({ id:"1", label:"Photo", required:true, responseType:"photo", value:null, photoAttached:false })).toBe(false);
    expect(isItemComplete({ id:"1", label:"Photo", required:true, responseType:"photo", value:null, photoAttached:true })).toBe(true);
  });

  it("treats a text/numeric/pass_fail item complete only when value is non-empty", () => {
    expect(isItemComplete({ id:"1", label:"Voltage", required:true, responseType:"numeric", value:null, photoAttached:false })).toBe(false);
    expect(isItemComplete({ id:"1", label:"Voltage", required:true, responseType:"numeric", value:"220", photoAttached:false })).toBe(true);
  });
});

describe("computeProgress", () => {
  it("returns 0 for an empty checklist", () => {
    expect(computeProgress(view([]))).toBe(0);
  });

  it("computes a percentage of completed items", () => {
    const v = view([
      { id:"1", label:"A", required:true, responseType:"pass_fail", value:"pass", photoAttached:false },
      { id:"2", label:"B", required:true, responseType:"pass_fail", value:null, photoAttached:false },
    ]);
    expect(computeProgress(v)).toBe(50);
  });
});

describe("missingRequiredItems / canComplete", () => {
  it("reports missing required items and blocks completion", () => {
    const v = view([
      { id:"1", label:"A", required:true, responseType:"text", value:null, photoAttached:false },
      { id:"2", label:"B", required:false, responseType:"text", value:null, photoAttached:false },
    ]);
    expect(missingRequiredItems(v).map(i => i.id)).toEqual(["1"]);
    expect(canComplete(v)).toBe(false);
  });

  it("allows completion once all required items are complete regardless of optional ones", () => {
    const v = view([
      { id:"1", label:"A", required:true, responseType:"text", value:"ok", photoAttached:false },
      { id:"2", label:"B", required:false, responseType:"text", value:null, photoAttached:false },
    ]);
    expect(canComplete(v)).toBe(true);
  });
});
