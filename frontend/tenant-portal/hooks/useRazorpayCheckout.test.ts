import { renderHook } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { useRazorpayCheckout } from "./useRazorpayCheckout";

const order = { keyId: "rzp_test_key", orderId: "order_test", amountPaise: 10000, name: "Provider seats" };
afterEach(() => { delete window.Razorpay; document.querySelectorAll('script[src*="razorpay"]').forEach(s => s.remove()); vi.useRealTimers(); });

it.each([{ ...order, keyId: "" }, { ...order, orderId: "order_local_placeholder" }])("rejects incomplete server checkout configuration without opening an overlay", async invalid => {
  const constructor = vi.fn();
  window.Razorpay = class { constructor() { constructor(); } open() {} };
  const { result } = renderHook(() => useRazorpayCheckout());
  await expect(result.current.open(invalid)).rejects.toThrow(/configured|configuration/);
  expect(constructor).not.toHaveBeenCalled();
});

it("allows dismissal without reporting a successful payment", async () => {
  let options: any;
  window.Razorpay = class { constructor(opts: any) { options = opts; } open() {} };
  const { result } = renderHook(() => useRazorpayCheckout());
  const pending = result.current.open(order);
  const rejected = expect(pending).rejects.toThrow(/closed|cancel/i);
  await Promise.resolve();
  options.modal.ondismiss();
  await rejected;
});

it("opens an overlay without redirecting and resolves signed payment details", async () => {
  let options: any;
  const open = vi.fn();
  window.Razorpay = class { constructor(opts: any) { options = opts; } open = open; };
  const { result } = renderHook(() => useRazorpayCheckout());
  const pending = result.current.open(order);
  await Promise.resolve();
  expect(open).toHaveBeenCalledOnce();
  expect(options.redirect).toBe(false);
  expect(options.modal.escape).toBe(true);
  const payment = { razorpay_order_id: order.orderId, razorpay_payment_id: "pay_test", razorpay_signature: "signed" };
  options.handler(payment);
  await expect(pending).resolves.toEqual(payment);
});

it("rejects failed payments and closes checkout so the page can recover", async () => {
  let failed: any;
  const close = vi.fn();
  window.Razorpay = class { open() {} close = close; on(_event: string, handler: any) { failed = handler; } };
  const { result } = renderHook(() => useRazorpayCheckout());
  const pending = result.current.open(order);
  const rejected = expect(pending).rejects.toThrow("Bank declined");
  await Promise.resolve();
  failed({ error: { description: "Bank declined" } });
  await rejected;
  expect(close).toHaveBeenCalledOnce();
});

it("times out a stuck script and permits a fresh attempt", async () => {
  vi.useFakeTimers();
  const { result } = renderHook(() => useRazorpayCheckout());
  const pending = result.current.open(order);
  const rejected = expect(pending).rejects.toThrow("timed out");
  await vi.advanceTimersByTimeAsync(20000);
  await rejected;
  expect(document.querySelector('script[src*="razorpay"]')).toBeNull();
  const retry = result.current.open(order);
  const retryRejected = expect(retry).rejects.toThrow("Could not load");
  document.querySelector('script[src*="razorpay"]')!.dispatchEvent(new Event("error"));
  await retryRejected;
});
