import { AccessibilityInfo } from "react-native";

export type ToastType = "success" | "info" | "warning" | "error";

export interface ToastMessage {
  id: string;
  type: ToastType;
  message: string;
  timeoutMs: number;
}

type Listener = (toasts: ToastMessage[]) => void;

const DEFAULT_TIMEOUT_MS = 3500;

let queue: ToastMessage[] = [];
const listeners = new Set<Listener>();

function notify() {
  listeners.forEach((listener) => listener(queue));
}

function newId(): string {
  return `toast_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

/**
 * Centralized toast/snackbar interface. Business screens must call these
 * functions instead of reaching for a toast library directly, so there is
 * exactly one queue, one accessibility announcement path, and one visual style.
 */
export const toastService = {
  subscribe(listener: Listener): () => void {
    listeners.add(listener);
    listener(queue);
    return () => listeners.delete(listener);
  },

  show(type: ToastType, message: string, timeoutMs: number = DEFAULT_TIMEOUT_MS): string {
    const toast: ToastMessage = { id: newId(), type, message, timeoutMs };
    queue = [...queue, toast];
    notify();
    AccessibilityInfo.announceForAccessibility?.(message);
    return toast.id;
  },

  dismiss(id: string): void {
    queue = queue.filter((toast) => toast.id !== id);
    notify();
  },

  success: (message: string) => toastService.show("success", message),
  info: (message: string) => toastService.show("info", message),
  warning: (message: string) => toastService.show("warning", message),
  error: (message: string) => toastService.show("error", message),
};
