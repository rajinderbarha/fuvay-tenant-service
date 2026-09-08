import { expect, it } from "vitest";
import { resolveTenantNavId } from "./nav-config";
import { resolveTenantPageMeta } from "./page-registry";

it("keeps Direct Payments within Finance & Credits with the reference breadcrumb", () => {
  expect(resolveTenantNavId("/home-services/direct-payments")).toBe("hs-finance");
  expect(resolveTenantPageMeta("/home-services/direct-payments")?.breadcrumbs).toEqual([{ label: "Direct Payments" }]);
});
