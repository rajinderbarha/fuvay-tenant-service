"use client";

import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ChevronDown, MoreHorizontal } from "lucide-react";

export interface ActionMenuItem {
  label: string;
  icon?: React.ReactNode;
  onClick?: () => void;
  href?: string;
  variant?: "default" | "danger";
  /** @deprecated Use `variant: "danger"`. */
  destructive?: boolean;
  disabled?: boolean;
  divider?: boolean;
}

type MenuPosition = { top: number; left: number; minWidth: number };

export function ActionMenu({
  items,
  label = "Actions",
  icon,
  align = "right",
  size = "sm",
}: {
  items: Array<ActionMenuItem | null | false | undefined>;
  label?: string;
  icon?: React.ReactNode;
  align?: "left" | "right";
  size?: "xs" | "sm" | "md";
}) {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState<MenuPosition | null>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const visibleItems = items.filter(Boolean) as ActionMenuItem[];

  const placeMenu = useCallback(() => {
    const trigger = triggerRef.current;
    if (!trigger) return;
    const rect = trigger.getBoundingClientRect();
    const viewportPadding = 8;
    const minWidth = Math.max(200, rect.width);
    const measuredHeight = menuRef.current?.offsetHeight ?? Math.min(visibleItems.length * 42 + 8, 360);
    const openAbove = window.innerHeight - rect.bottom < measuredHeight + viewportPadding && rect.top > measuredHeight;
    const rawLeft = align === "right" ? rect.right - minWidth : rect.left;
    setPosition({
      top: openAbove ? Math.max(viewportPadding, rect.top - measuredHeight - 6) : Math.min(window.innerHeight - viewportPadding, rect.bottom + 6),
      left: Math.max(viewportPadding, Math.min(rawLeft, window.innerWidth - minWidth - viewportPadding)),
      minWidth,
    });
  }, [align, visibleItems.length]);

  useLayoutEffect(() => {
    if (open) placeMenu();
  }, [open, placeMenu]);

  useEffect(() => {
    if (!open) return;
    const dismiss = (event: MouseEvent) => {
      const target = event.target as Node;
      if (!triggerRef.current?.contains(target) && !menuRef.current?.contains(target)) setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("mousedown", dismiss);
    document.addEventListener("keydown", onKeyDown);
    window.addEventListener("resize", placeMenu);
    window.addEventListener("scroll", placeMenu, true);
    return () => {
      document.removeEventListener("mousedown", dismiss);
      document.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("resize", placeMenu);
      window.removeEventListener("scroll", placeMenu, true);
    };
  }, [open, placeMenu]);

  if (visibleItems.length === 0) return null;

  const dimensions = {
    xs: { height: 28, padding: "0 8px", fontSize: 11 },
    sm: { height: 32, padding: "0 10px", fontSize: 12 },
    md: { height: 38, padding: "0 12px", fontSize: 13 },
  }[size];
  const compactTrigger = label === "Actions" && !icon;

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        className="ds-action-menu-trigger"
        onClick={event => {
          event.stopPropagation();
          setOpen(value => !value);
        }}
        style={{ ...dimensions, width: compactTrigger ? dimensions.height : undefined }}
        aria-label={label}
        aria-expanded={open}
        aria-haspopup="menu"
      >
        {icon ?? <MoreHorizontal size={16} />}
        {!compactTrigger && <span>{label}</span>}
        {!compactTrigger && <ChevronDown size={13} />}
      </button>

      {open && position && createPortal(
        <div
          ref={menuRef}
          role="menu"
          className="ds-action-menu"
          style={{ top: position.top, left: position.left, minWidth: position.minWidth }}
          onClick={event => event.stopPropagation()}
        >
          {visibleItems.map((item, index) => (
            <React.Fragment key={`${item.label}-${index}`}>
              {item.divider && index > 0 && <div className="ds-action-menu-divider" />}
              <button
                type="button"
                role="menuitem"
                disabled={item.disabled}
                className={item.variant === "danger" || item.destructive ? "is-danger" : undefined}
                onClick={() => {
                  if (item.disabled) return;
                  setOpen(false);
                  if (item.href) window.location.assign(item.href);
                  else item.onClick?.();
                }}
              >
                {item.icon && <span className="ds-action-menu-icon">{item.icon}</span>}
                <span>{item.label}</span>
              </button>
            </React.Fragment>
          ))}
        </div>,
        document.body,
      )}
    </>
  );
}

