import { get, post } from "./client";
import type { DashboardConfig, DashboardStats } from "../types/dashboard";
import type { ApiResponse } from "../types/api";
import { REFRESH_INTERVAL_MS } from "../utils/constants";

export async function getDashboard(id: string): Promise<ApiResponse<DashboardConfig>> {
  return get<DashboardConfig>(`/dashboards/${id}`);
}

export async function listDashboards(): Promise<ApiResponse<DashboardConfig[]>> {
  return get<DashboardConfig[]>("/dashboards");
}

export async function createDashboard(config: Omit<DashboardConfig, "id">): Promise<ApiResponse<DashboardConfig>> {
  return post<DashboardConfig>("/dashboards", config);
}

export async function getDashboardStats(): Promise<ApiResponse<DashboardStats>> {
  return get<DashboardStats>("/dashboards/stats");
}

export function createPollingFetcher(id: string, onData: (s: DashboardStats) => void): () => void {
  const timer = setInterval(async () => {
    const res = await getDashboardStats();
    if (res.data) onData(res.data);
  }, REFRESH_INTERVAL_MS);
  return () => clearInterval(timer);
}
