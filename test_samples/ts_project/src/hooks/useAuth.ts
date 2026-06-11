import { useState, useEffect, useCallback } from "react";
import { loginUser, logoutUser, getMe } from "../api/userApi";
import type { User, UserCredentials } from "../types/user";
import { TOKEN_STORAGE_KEY } from "../utils/constants";

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    user: null,
    token: localStorage.getItem(TOKEN_STORAGE_KEY),
    isLoading: false,
    error: null,
  });

  useEffect(() => {
    if (state.token && !state.user) {
      setState((s) => ({ ...s, isLoading: true }));
      getMe()
        .then((res) => setState((s) => ({ ...s, user: res.data, isLoading: false })))
        .catch(() => setState((s) => ({ ...s, token: null, isLoading: false })));
    }
  }, [state.token]);

  const login = useCallback(async (credentials: UserCredentials) => {
    setState((s) => ({ ...s, isLoading: true, error: null }));
    try {
      const res = await loginUser(credentials);
      setState({ user: res.data.user, token: res.data.token, isLoading: false, error: null });
    } catch (err: unknown) {
      setState((s) => ({ ...s, isLoading: false, error: "Login failed" }));
    }
  }, []);

  const logout = useCallback(async () => {
    await logoutUser();
    setState({ user: null, token: null, isLoading: false, error: null });
  }, []);

  return { ...state, login, logout };
}
