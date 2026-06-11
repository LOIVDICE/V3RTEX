import React from "react";
import type { User } from "../../types/user";
import { useAuth } from "../../hooks";
import { Button } from "../ui/Button";
import { formatRelativeTime } from "../../utils/formatters";

interface HeaderProps {
  title: string;
}

export function Header({ title }: HeaderProps) {
  const { user, logout } = useAuth();

  return (
    <header className="header">
      <h1>{title}</h1>
      {user && (
        <div className="header-user">
          <span>{user.username}</span>
          <span className="badge">{user.role}</span>
          <span className="muted">{formatRelativeTime(user.createdAt)}</span>
          <Button label="Logout" onClick={logout} variant="secondary" />
        </div>
      )}
    </header>
  );
}

export default Header;
