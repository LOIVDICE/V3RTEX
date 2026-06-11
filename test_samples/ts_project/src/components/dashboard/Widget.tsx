import React from "react";
import type { WidgetConfig } from "../../types/dashboard";
import { formatNumber, formatCurrency } from "../../utils/formatters";

interface WidgetProps {
  config: WidgetConfig;
  value?: number;
  isLoading?: boolean;
}

export function Widget({ config, value, isLoading }: WidgetProps) {
  const formatted = config.type === "stat" && value != null
    ? config.dataSource.includes("revenue")
      ? formatCurrency(value)
      : formatNumber(value)
    : null;

  return (
    <div className={`widget widget-${config.type} col-span-${config.width ?? 1}`}>
      <h3>{config.title}</h3>
      {isLoading && <div className="skeleton" />}
      {!isLoading && formatted && <div className="stat-value">{formatted}</div>}
      {!isLoading && !formatted && <div className="widget-placeholder">No data</div>}
    </div>
  );
}

export default Widget;
