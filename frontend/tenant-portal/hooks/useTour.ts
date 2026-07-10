"use client";
import { useState, useEffect, useCallback } from "react";
export interface TourStep { id:string; targetId:string; title:string; description:string; position:"bottom"|"right"|"left"|"top"; }
export const TOUR_STEPS: TourStep[] = [
  { id:"step-1", targetId:"nav-dashboard",  title:"Your Daily Command", description:"Jobs, bookings, wallet and performance — your complete business picture at a glance. Red numbers need action today.", position:"right" },
  { id:"step-2", targetId:"kpi-jobs-today", title:"Today's Jobs", description:"Every job your team is working on right now. Click to see the full 23-status timeline and assign staff.", position:"bottom" },
  { id:"step-3", targetId:"nav-bookings",   title:"Incoming Bookings", description:"New customer bookings waiting for your confirmation. Accept, reject or reschedule — each with one click.", position:"right" },
  { id:"step-4", targetId:"nav-staff",      title:"Your Team", description:"Staff roster, performance scores, live locations, and working hours. All performance data from the AI engine.", position:"right" },
  { id:"step-5", targetId:"nav-finance",    title:"Wallet & Commission", description:"Your credit wallet balance, commission history per job, and invoice downloads. Top up and pay out from here.", position:"right" },
  { id:"step-6", targetId:"nav-reviews",    title:"Customer Reviews", description:"Incoming star ratings with 5-signal breakdown. Reply once per review. Your aggregate score updates in real time.", position:"right" },
  { id:"step-7", targetId:"nav-settings",   title:"Your Settings", description:"Three levels shown — your overrides, plan defaults, and platform defaults. Change only what you need.", position:"right" },
];
const TOUR_KEY = "serviceos-tenant-tour-done";
export function useTour() {
  const [active,setActive]=useState(false);
  const [step,setStep]=useState(0);
  const [mounted,setMounted]=useState(false);
  useEffect(()=>{ setMounted(true); if(!localStorage.getItem(TOUR_KEY))setActive(true); },[]);
  const next    = useCallback(()=>{ if(step<TOUR_STEPS.length-1)setStep(s=>s+1); else complete(); },[step]);
  const prev    = useCallback(()=>{ if(step>0)setStep(s=>s-1); },[step]);
  const complete= useCallback(()=>{ setActive(false); localStorage.setItem(TOUR_KEY,"true"); },[]);
  const restart = useCallback(()=>{ localStorage.removeItem(TOUR_KEY); setStep(0); setActive(true); },[]);
  return { active, step, mounted, currentStep:TOUR_STEPS[step], totalSteps:TOUR_STEPS.length,
    next, prev, skip:complete, complete, restart, isFirst:step===0, isLast:step===TOUR_STEPS.length-1 };
}
