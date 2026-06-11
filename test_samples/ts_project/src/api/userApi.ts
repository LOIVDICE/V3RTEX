import { get, post, put, del } from "./client";
import type { User, UserCredentials, CreateUserPayload } from "../types/user";
import type { ApiResponse, PaginatedResponse, PaginationParams } from "../types/api";
import { TOKEN_STORAGE_KEY } from "../utils/constants";

export async function loginUser(credentials: UserCredentials): Promise<ApiResponse<{ token: string; user: User }>> {
  const res = await post<{ token: string; user: User }>("/auth/login", credentials);
  if (res.data?.token) localStorage.setItem(TOKEN_STORAGE_KEY, res.data.token);
  return res;
}

export async function logoutUser(): Promise<void> {
  await post("/auth/logout", {});
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

export async function getMe(): Promise<ApiResponse<User>> {
  return get<User>("/auth/me");
}

export async function getUser(id: number): Promise<ApiResponse<User>> {
  return get<User>(`/users/${id}`);
}

export async function listUsers(params: PaginationParams = {}): Promise<ApiResponse<PaginatedResponse<User>>> {
  return get<PaginatedResponse<User>>("/users", { params });
}

export async function createUser(payload: CreateUserPayload): Promise<ApiResponse<User>> {
  return post<User>("/users", payload);
}

export async function deactivateUser(id: number): Promise<ApiResponse<void>> {
  return del<void>(`/users/${id}`);
}
