export const API_BASE_URL = process.env.REACT_APP_API_URL ?? "http://localhost:8000";
export const MAX_ITEMS_PER_PAGE = 100;
export const DEFAULT_PAGE_SIZE = 20;
export const TOKEN_STORAGE_KEY = "auth_token";
export const REFRESH_INTERVAL_MS = 30_000;
export const SUPPORTED_CHART_TYPES = ["bar", "line", "pie", "area"] as const;
