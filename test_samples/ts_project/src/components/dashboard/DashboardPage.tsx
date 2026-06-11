import React from "react";
import { useDashboard } from "../../hooks";
import { Widget } from "./Widget";
import { Header } from "../layout/Header";
import type { DashboardConfig } from "../../types/dashboard";
import { formatNumber } from "../../utils/formatters";

interface DashboardPageProps {
  dashboardId: string;
}

export function DashboardPage({ dashboardId }: DashboardPageProps) {
  const { config, stats, isLoading, error } = useDashboard(dashboardId);

  if (error) return <div className="error">{error}</div>;

  const statMap: Record<string, number | undefined> = {
    totalUsers:   stats?.totalUsers,
    activeUsers:  stats?.activeUsers,
    totalOrders:  stats?.totalOrders,
    revenue:      stats?.revenue,
  };

  return (
    <div className="dashboard">
      <Header title={config?.name ?? "Dashboard"} />
      {config && (
        <div className={`grid layout-${config.layout}`}>
          {config.widgets.map((w) => (
            <Widget
              key={w.id}
              config={w}
              value={statMap[w.dataSource]}
              isLoading={isLoading}
            />
          ))}
        </div>
      )}
      {stats && (
        <footer className="stats-footer">
          {formatNumber(stats.totalUsers)} total users · {formatNumber(stats.totalOrders)} orders
        </footer>
      )}
    </div>
  );
}

export default DashboardPage;
