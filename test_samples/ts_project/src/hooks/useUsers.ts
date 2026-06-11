import { useState, useCallback } from "react";
import * as userApi from "../api/userApi";
import type { User, CreateUserPayload } from "../types/user";
import type { PaginatedResponse, PaginationParams } from "../types/api";
import { DEFAULT_PAGE_SIZE } from "../utils/constants";

export function useUsers() {
  const [users, setUsers] = useState<PaginatedResponse<User> | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchUsers = useCallback(async (params: PaginationParams = { size: DEFAULT_PAGE_SIZE }) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await userApi.listUsers(params);
      setUsers(res.data);
    } catch {
      setError("Failed to fetch users");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const createUser = useCallback(async (payload: CreateUserPayload): Promise<User | null> => {
    try {
      const res = await userApi.createUser(payload);
      return res.data;
    } catch {
      setError("Failed to create user");
      return null;
    }
  }, []);

  const deactivateUser = useCallback(async (id: number): Promise<boolean> => {
    try {
      await userApi.deactivateUser(id);
      return true;
    } catch {
      return false;
    }
  }, []);

  return { users, isLoading, error, fetchUsers, createUser, deactivateUser };
}
