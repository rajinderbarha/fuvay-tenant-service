import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ProviderDetailWorkspace } from "./ProviderDetailWorkspace";
const state = vi.hoisted(() => ({ tab: "overview" }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), back: vi.fn() }), useSearchParams: () => new URLSearchParams({tab:state.tab}) }));
vi.mock("../layout/AdminLayout", () => ({AdminLayout: ({children}:any) => <div>{children}</div>}));
vi.mock("../../lib/api", () => ({
  ServiceOSError: class extends Error {},
  hsProviderDirectoryApi: {
    getDetail: async () => ({business_name:"Test Provider",registration_status:"under_review",verification_status:"pending",is_discoverable:true,is_bookable:false,profile_completion_percentage:100,setup_sections:[],readiness:{setup_complete:true,enrollment_active:false},bookability_blockers:[]}),
    getFinance: async () => ({usage_credits:{balance:5000},technician_seats:{entitled:3,used:1,available:2},plan_purchase_history:[{id:"p",seats_granted:3,status:"captured",amount:5900,credited_amount:5000}]}),
    getTeam: async () => ({total_staff:1,technician_count:1,available_staff:1,staff:[{staff_id:"s",name:"No-login technician",designation:"technician",login_status:"Not created",can_receive_assignment:true}]}),
    getServices: async () => ({services:[{tenant_service_id:"off",master_service_name:"Unoffered service",is_enabled:false,is_active:true,price_configured:false}],missing_price_config_count:0,business_hours:[],schedule_exceptions:[]}),
    getActivity: async () => ({documents:[],events:[]}),
    getOperations: async () => ({jobs:[],by_status:{}}), getQuality: async () => ({complaints:[],health_score:100,health_band:"gold"}),
  },
  hsReviewApi:{getProviderReviewSummary:async()=>({})},
  verticalCatalogApi:{listEnrollments:async()=>({items:[{id:"en",status:"submitted"}]}),transitionEnrollment:vi.fn()},
}));
beforeEach(()=>{state.tab="overview";});
afterEach(cleanup);
const open = () => render(<ProviderDetailWorkspace providerId="provider" basePath="/admin/home-services/providers"/>);
it("shows 100% setup without claiming a submitted provider is bookable",async()=>{
  open(); await screen.findByRole("heading",{name:"Test Provider"});
  expect(screen.getByText("Setup completion: 100%")).toBeInTheDocument();
  expect(screen.getByText("Not Bookable")).toBeInTheDocument();
  expect(screen.getByRole("button",{name:"Suspend Home Services"})).toBeDisabled();
});
it.each(["verification","services","team","operations","finance","quality","documents"])("renders the %s tab",async tab=>{
  state.tab=tab; open(); await screen.findByRole("heading",{name:"Test Provider"});
  if(tab==="team") expect(await screen.findByText("No-login technician")).toBeInTheDocument();
  if(tab==="services") expect(await screen.findByText("Unoffered service")).toBeInTheDocument();
  if(tab==="finance") expect(await screen.findByText("Technician plan orders")).toBeInTheDocument();
  if(tab==="documents") expect(await screen.findByText("No documents uploaded yet.")).toBeInTheDocument();
  if(tab==="verification") expect(await screen.findByText("Business identity")).toBeInTheDocument();
  if(tab==="operations") expect(await screen.findByText("No Home Services jobs recorded for this provider yet.")).toBeInTheDocument();
  if(tab==="quality") expect(await screen.findByText("No complaints recorded for this provider.")).toBeInTheDocument();
});
