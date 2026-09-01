import React from "react";

export type TableDensity = "compact" | "standard" | "comfortable";

export type TableSurfaceProps = React.TableHTMLAttributes<HTMLTableElement> & {
  density?: TableDensity;
};

/**
 * Canonical semantic table element for admin and tenant workspaces.
 *
 * Feature pages keep ownership of their columns and cell content while the
 * design system owns density, typography, borders, hover/focus behavior and
 * responsive overflow. Menus must use the shared portal-based ActionMenu so
 * they are never clipped by a table's scroll container.
 */
export function TableSurface({
  density = "standard",
  className,
  style,
  children,
  ...tableProps
}: TableSurfaceProps) {
  return (
    <div className="ds-table-viewport" tabIndex={0}>
      <table
        {...tableProps}
        data-density={density}
        className={["ds-table", className].filter(Boolean).join(" ")}
        style={style}
      >
        {children}
      </table>
    </div>
  );
}
