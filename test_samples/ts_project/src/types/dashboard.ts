export type WidgetType = "chart" | "table" | "stat" | "map";

export interface WidgetConfig {
  id: string;
  type: WidgetType;
  title: string;
  dataSource: string;
  refreshInterval?: number;
  width?: 1 | 2 | 3 | 4;
}

export interface DashboardConfig {
  id: string;
  name: string;
  widgets: WidgetConfig[];
  layout: "grid" | "list";
  isPublic: boolean;
}

export interface DashboardStats {
  totalUsers: number;
  activeUsers: number;
  totalOrders: number;
  revenue: number;
}
