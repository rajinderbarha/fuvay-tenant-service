/**
 * useToast — global notification toast hook.
 * Wraps toast state — components call addToast, never manage state themselves.
 */
import { useState, useCallback, useRef } from "react";

export type ToastVariant = "success" | "warning" | "danger" | "info" | "default";
export interface Toast {
  id: string;
  title: string;
  description?: string;
  variant: ToastVariant;
  duration?: number;
}

export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const idRef = useRef(0);

  const addToast = useCallback((toast: Omit<Toast, "id">) => {
    const id = String(++idRef.current);
    const item: Toast = { id, duration: 4000, ...toast };
    setToasts(prev => [...prev, item]);
    setTimeout(() => removeToast(id), item.duration);
    return id;
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  return { toasts, addToast, removeToast };
}
