import React, { Suspense, lazy } from "react";
import { useAuth } from "./hooks";
import { Header } from "./components/layout/Header";
import { Button } from "./components/ui/Button";
import type { User } from "./types/user";

// Dynamic import — stress-tests resolver's handling of import()
const DashboardPage = lazy(() => import("./components/dashboard/DashboardPage"));

function LoginPrompt() {
  const { login, isLoading, error } = useAuth();
  return (
    <div className="login-prompt">
      <h2>Sign in</h2>
      {error && <p className="error">{error}</p>}
      <Button
        label={isLoading ? "Signing in…" : "Sign in"}
        onClick={() => login({ email: "demo@example.com", password: "Demo1234" })}
        disabled={isLoading}
      />
    </div>
  );
}

export default function App() {
  const { user } = useAuth();

  return (
    <div className="app">
      <Header title="Dashboard" />
      <main>
        {user ? (
          <Suspense fallback={<div>Loading…</div>}>
            <DashboardPage dashboardId="default" />
          </Suspense>
        ) : (
          <LoginPrompt />
        )}
      </main>
    </div>
  );
}
