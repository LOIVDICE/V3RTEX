import { useState, useEffect, useReducer } from "react";
import { getDashboard, getDashboardStats, createPollingFetcher } from "../api/dashboardApi";
import type { DashboardConfig, DashboardStats } from "../types/dashboard";

type Action =
  | { type: "SET_CONFIG"; payload: DashboardConfig }
  | { type: "SET_STATS"; payload: DashboardStats }
  | { type: "SET_ERROR"; payload: string }
  | { type: "SET_LOADING"; payload: boolean };

interface DashboardState {
  config: DashboardConfig | null;
  stats: DashboardStats | null;
  isLoading: boolean;
  error: string | null;
}

function reducer(state: DashboardState, action: Action): DashboardState {
  switch (action.type) {
    case "SET_CONFIG":  return { ...state, config: action.payload };
    case "SET_STATS":   return { ...state, stats: action.payload };
    case "SET_ERROR":   return { ...state, error: action.payload, isLoading: false };
    case "SET_LOADING": return { ...state, isLoading: action.payload };
    default:            return state;
  }
}

export function useDashboard(dashboardId: string) {
  const [state, dispatch] = useReducer(reducer, {
    config: null, stats: null, isLoading: true, error: null,
  });

  useEffect(() => {
    dispatch({ type: "SET_LOADING", payload: true });
    Promise.all([getDashboard(dashboardId), getDashboardStats()])
      .then(([configRes, statsRes]) => {
        dispatch({ type: "SET_CONFIG", payload: configRes.data });
        dispatch({ type: "SET_STATS",  payload: statsRes.data });
        dispatch({ type: "SET_LOADING", payload: false });
      })
      .catch((err) => dispatch({ type: "SET_ERROR", payload: String(err) }));

    return createPollingFetcher(dashboardId, (s) =>
      dispatch({ type: "SET_STATS", payload: s })
    );
  }, [dashboardId]);

  return state;
}
