import "@testing-library/jest-dom/vitest";
import React from "react";
import { vi } from "vitest";

// next/link pulls Next's nested React runtime, which is intentionally
// separate from the hoisted jsdom renderer in this workspace. For component
// tests a semantic anchor is the correct boundary and keeps one React copy.
vi.mock("next/link", () => ({
  default: ({ href, children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) =>
    React.createElement("a", { href, ...props }, children),
}));
