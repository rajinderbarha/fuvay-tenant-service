"use client";
/**
 * useRazorpayCheckout — loads Razorpay's Checkout.js once and exposes a
 * Promise-based open() call. Resolves with the payment fields Razorpay
 * returns on success; rejects if the user dismisses the popup or payment fails.
 */
import { useCallback, useRef } from "react";

declare global {
  interface Window {
    Razorpay?: new (options: RazorpayOptions) => { open: () => void; close?: () => void; on?: (event: string, handler: (response: { error?: { description?: string } }) => void) => void };
  }
}

export interface RazorpayResult {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}

interface RazorpayOptions {
  key: string;
  amount: number;
  currency: string;
  name: string;
  description?: string;
  order_id: string;
  handler: (response: RazorpayResult) => void;
  prefill?: { name?: string; email?: string; contact?: string };
  theme?: { color?: string };
  redirect?: boolean;
  timeout?: number;
  modal?: { ondismiss?: () => void; escape?: boolean; backdropclose?: boolean; confirm_close?: boolean };
}

const CHECKOUT_SRC = "https://checkout.razorpay.com/v1/checkout.js";

let scriptPromise: Promise<void> | null = null;
function loadScript(): Promise<void> {
  if (typeof window === "undefined") return Promise.reject(new Error("No window"));
  if (window.Razorpay) return Promise.resolve();
  if (scriptPromise) return scriptPromise;
  scriptPromise = new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${CHECKOUT_SRC}"]`);
    const script = existing ?? document.createElement("script");
    const finish = (error?: Error) => {
      clearTimeout(timer);
      script.removeEventListener("load", loaded);
      script.removeEventListener("error", failed);
      if (error) { script.remove(); reject(error); } else resolve();
    };
    const loaded = () => finish(window.Razorpay ? undefined : new Error("Razorpay checkout is unavailable. Please retry."));
    const failed = () => finish(new Error("Could not load secure checkout. Check your connection or content blocker and retry."));
    const timer = setTimeout(() => finish(new Error("Secure checkout timed out loading. Please retry.")), 20000);
    script.src = CHECKOUT_SRC;
    script.async = true;
    script.addEventListener("load", loaded);
    script.addEventListener("error", failed);
    if (!existing) document.body.appendChild(script);
  }).finally(() => { scriptPromise = null; });
  return scriptPromise;
}

export function useRazorpayCheckout() {
  const loadingRef = useRef<Promise<void> | null>(null);

  const open = useCallback(async (opts: {
    keyId: string; orderId: string; amountPaise: number; currency?: string;
    name: string; description?: string;
    prefill?: { name?: string; email?: string; contact?: string };
  }): Promise<RazorpayResult> => {
    if (!opts.keyId || !opts.orderId || !Number.isFinite(opts.amountPaise) || opts.amountPaise <= 0) throw new Error("Checkout order is incomplete. Refresh your plan and try again.");
    if (!loadingRef.current) loadingRef.current = loadScript();
    try { await loadingRef.current; } finally { loadingRef.current = null; }
    if (!window.Razorpay) throw new Error("Razorpay checkout failed to load.");

    return new Promise<RazorpayResult>((resolve, reject) => {
      const rzp = new window.Razorpay!({
        key: opts.keyId,
        amount: opts.amountPaise,
        currency: opts.currency ?? "INR",
        name: opts.name,
        description: opts.description,
        order_id: opts.orderId,
        prefill: opts.prefill,
        theme: { color: "#0F766E" },
        redirect: false,
        timeout: 600,
        handler: (response) => resolve(response),
        modal: { escape: true, backdropclose: false, confirm_close: true, ondismiss: () => reject(new Error("Payment cancelled.")) },
      });
      rzp.on?.("payment.failed", response => {
        reject(new Error(response.error?.description || "Payment failed. Please retry."));
        rzp.close?.();
      });
      rzp.open();
    });
  }, []);

  return { open };
}
