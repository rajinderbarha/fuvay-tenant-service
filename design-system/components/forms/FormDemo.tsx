"use client";
/**
 * FormDemo — reference example consuming FormShell with all field types.
 * Shows Input, Select, Textarea, Checkbox, Switch in a real form.
 */
import React, { useState } from "react";
import { FormShell } from "./FormShell";
export interface FormDemoProps { onSubmit?: (data: Record<string,unknown>)=>void; loading?: boolean; error?: string; success?: string; }
export function FormDemo({ onSubmit, loading, error, success }: FormDemoProps) {
  const [name,     setName]     = useState("");
  const [email,    setEmail]    = useState("");
  const [vertical, setVertical] = useState("");
  const [city,     setCity]     = useState("");
  const [notes,    setNotes]    = useState("");
  const [agree,    setAgree]    = useState(false);
  const [errors, setErrors] = useState<Record<string,string>>({});
  function validate() {
    const e: Record<string,string> = {};
    if (!name.trim())  e.name  = "Business name is required";
    if (!email.trim()) e.email = "Email is required";
    if (!/^[^@]+@[^@]+\.[^@]+$/.test(email)) e.email = "Enter a valid email";
    if (!vertical) e.vertical = "Select a vertical";
    if (!agree)    e.agree    = "You must agree to continue";
    setErrors(e); return Object.keys(e).length === 0;
  }
  function handleSubmit(e: React.FormEvent) {
    e.preventDefault(); if (!validate()) return;
    onSubmit?.({ name, email, vertical, city, notes, agree });
  }
  return (
    <FormShell
      title="Onboard New Tenant" subtitle="Fill in the details to create a new tenant workspace."
      submitLabel="Create Tenant" onSubmit={handleSubmit}
      loading={loading} error={error} success={success}
      sections={[
        {
          title:"Business Details", description:"Basic information about the business.", cols:2,
          fields: <>
            <div>
              <label style={{ fontSize:"var(--text-sm)", fontWeight:"var(--font-medium)", color:"var(--color-text-secondary)", display:"block", marginBottom:5 }}>Business Name *</label>
              <input value={name} onChange={e=>setName(e.target.value)} placeholder="Rahul AC Services"
                style={{ width:"100%", height:38, padding:"0 12px", fontSize:"var(--text-base)",
                  fontFamily:"var(--font-sans)", background:"var(--input-bg)",
                  border:`1px solid ${errors.name?"var(--color-danger)":"var(--input-border)"}`,
                  borderRadius:"var(--radius-md)", color:"var(--color-text-primary)",
                  outline:"none", boxSizing:"border-box" as const }}/>
              {errors.name && <p style={{ fontSize:"var(--text-xs)", color:"var(--color-danger-text)", margin:"4px 0 0" }}>{errors.name}</p>}
            </div>
            <div>
              <label style={{ fontSize:"var(--text-sm)", fontWeight:"var(--font-medium)", color:"var(--color-text-secondary)", display:"block", marginBottom:5 }}>Owner Email *</label>
              <input type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="owner@business.com"
                style={{ width:"100%", height:38, padding:"0 12px", fontSize:"var(--text-base)",
                  fontFamily:"var(--font-sans)", background:"var(--input-bg)",
                  border:`1px solid ${errors.email?"var(--color-danger)":"var(--input-border)"}`,
                  borderRadius:"var(--radius-md)", color:"var(--color-text-primary)",
                  outline:"none", boxSizing:"border-box" as const }}/>
              {errors.email && <p style={{ fontSize:"var(--text-xs)", color:"var(--color-danger-text)", margin:"4px 0 0" }}>{errors.email}</p>}
            </div>
            <div>
              <label style={{ fontSize:"var(--text-sm)", fontWeight:"var(--font-medium)", color:"var(--color-text-secondary)", display:"block", marginBottom:5 }}>Vertical *</label>
              <select value={vertical} onChange={e=>setVertical(e.target.value)}
                style={{ width:"100%", height:38, padding:"0 12px", fontSize:"var(--text-base)",
                  fontFamily:"var(--font-sans)", background:"var(--input-bg)",
                  border:`1px solid ${errors.vertical?"var(--color-danger)":"var(--input-border)"}`,
                  borderRadius:"var(--radius-md)", color:"var(--color-text-primary)",
                  outline:"none", boxSizing:"border-box" as const }}>
                <option value="">Select vertical…</option>
                <option value="home_services">Home Services</option>
                <option value="coaching_center">Coaching Center</option>
              </select>
              {errors.vertical && <p style={{ fontSize:"var(--text-xs)", color:"var(--color-danger-text)", margin:"4px 0 0" }}>{errors.vertical}</p>}
            </div>
            <div>
              <label style={{ fontSize:"var(--text-sm)", fontWeight:"var(--font-medium)", color:"var(--color-text-secondary)", display:"block", marginBottom:5 }}>City</label>
              <input value={city} onChange={e=>setCity(e.target.value)} placeholder="Mumbai"
                style={{ width:"100%", height:38, padding:"0 12px", fontSize:"var(--text-base)",
                  fontFamily:"var(--font-sans)", background:"var(--input-bg)",
                  border:"1px solid var(--input-border)", borderRadius:"var(--radius-md)",
                  color:"var(--color-text-primary)", outline:"none", boxSizing:"border-box" as const }}/>
            </div>
          </>
        },
        {
          title:"Additional Info",
          fields: <>
            <div>
              <label style={{ fontSize:"var(--text-sm)", fontWeight:"var(--font-medium)", color:"var(--color-text-secondary)", display:"block", marginBottom:5 }}>Notes</label>
              <textarea value={notes} onChange={e=>setNotes(e.target.value)} rows={3} placeholder="Any special requirements…"
                style={{ width:"100%", padding:"10px 12px", fontSize:"var(--text-base)",
                  fontFamily:"var(--font-sans)", background:"var(--input-bg)",
                  border:"1px solid var(--input-border)", borderRadius:"var(--radius-md)",
                  color:"var(--color-text-primary)", outline:"none", resize:"vertical",
                  boxSizing:"border-box" as const }}/>
            </div>
            <div>
              <label style={{ display:"flex", alignItems:"flex-start", gap:10,
                cursor:"pointer", userSelect:"none" as const }}>
                <div style={{ position:"relative", marginTop:2, flexShrink:0 }}>
                  <input type="checkbox" checked={agree} onChange={e=>setAgree(e.target.checked)}
                    style={{ position:"absolute", opacity:0, width:18, height:18, margin:0, cursor:"pointer" }}/>
                  <div style={{ width:18, height:18, borderRadius:"var(--radius-sm)",
                    border:`2px solid ${agree ? "var(--color-accent)" : errors.agree ? "var(--color-danger)" : "var(--color-border-strong)"}`,
                    background: agree ? "var(--color-accent)" : "var(--input-bg)",
                    display:"flex", alignItems:"center", justifyContent:"center", pointerEvents:"none" }}>
                    {agree && <svg width="10" height="8" viewBox="0 0 10 8" fill="none"><path d="M1 4L3.5 6.5L9 1" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>}
                  </div>
                </div>
                <span style={{ fontSize:"var(--text-sm)", color:"var(--color-text-primary)" }}>
                  I confirm this tenant has agreed to ServiceOS terms and has provided valid KYC documentation.
                </span>
              </label>
              {errors.agree && <p style={{ fontSize:"var(--text-xs)", color:"var(--color-danger-text)", margin:"4px 0 0", paddingLeft:28 }}>{errors.agree}</p>}
            </div>
          </>
        }
      ]}
    />
  );
}
