import axios, { AxiosInstance, AxiosRequestConfig } from "axios";
import { API_BASE_URL, TOKEN_STORAGE_KEY } from "../utils/constants";
import type { ApiResponse, ApiError } from "../types/api";

const instance: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10_000,
  headers: { "Content-Type": "application/json" },
});

instance.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_STORAGE_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export async function get<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
  const res = await instance.get<ApiResponse<T>>(url, config);
  return res.data;
}

export async function post<T>(url: string, body: unknown, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
  const res = await instance.post<ApiResponse<T>>(url, body, config);
  return res.data;
}

export async function put<T>(url: string, body: unknown, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
  const res = await instance.put<ApiResponse<T>>(url, body, config);
  return res.data;
}

export async function del<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
  const res = await instance.delete<ApiResponse<T>>(url, config);
  return res.data;
}

export default instance;
