"use client";
/**
 * useRazorpayCheckout — loads Razorpay's Checkout.js once and exposes a
 * Promise-based open() call. Resolves with the payment fields Razorpay
 * returns on success; rejects if the user dismisses the popup or payment fails.
 */
import { useCallback, useRef } from "react";

declare global {
  interface Window {
    Razorpay?: new (options: RazorpayOptions) => { open: () => void };
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
  modal?: { ondismiss?: () => void };
}

const CHECKOUT_SRC = "https://checkout.razorpay.com/v1/checkout.js";

function loadScript(): Promise<void> {
  if (typeof window === "undefined") return Promise.reject(new Error("No window"));
  if (window.Razorpay) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${CHECKOUT_SRC}"]`);
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () => reject(new Error("Failed to load Razorpay checkout script")));
      return;
    }
    const script = document.createElement("script");
    script.src = CHECKOUT_SRC;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Razorpay checkout script"));
    document.body.appendChild(script);
  });
}

export function useRazorpayCheckout() {
  const loadingRef = useRef<Promise<void> | null>(null);

  const open = useCallback(async (opts: {
    keyId: string; orderId: string; amountPaise: number; currency?: string;
    name: string; description?: string;
    prefill?: { name?: string; email?: string; contact?: string };
  }): Promise<RazorpayResult> => {
    if (!loadingRef.current) loadingRef.current = loadScript();
    await loadingRef.current;
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
        handler: (response) => resolve(response),
        modal: { ondismiss: () => reject(new Error("Payment cancelled.")) },
      });
      rzp.open();
    });
  }, []);

  return { open };
}
