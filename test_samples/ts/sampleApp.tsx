import React, { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { formatUserName } from "./formatters";

type UserRole = "admin" | "editor" | "viewer";

export type UserSummary = {
  id: number;
  label: string;
  isAdmin: boolean;
};

export interface UserRecord {
  id: number;
  name: string;
  roles: UserRole[];
  active?: boolean;
}

export enum LoadState {
  Idle = "idle",
  Loading = "loading",
  Error = "error",
  Ready = "ready",
}

function sealed(_: Function): void {
  // Sample decorator used to exercise decorator extraction.
}

@sealed
export abstract class Repository<T extends { id: number }> {
  protected items: T[];

  constructor(items: T[] = []) {
    this.items = items;
  }

  abstract load(): Promise<T[]>;

  findById(id: number): T | undefined {
    return this.items.find((item) => item.id === id);
  }
}

export class UserRepository extends Repository<UserRecord> {
  async load(): Promise<UserRecord[]> {
    const plugin = await import("./userPlugin");
    this.items = await plugin.loadUsers();
    return this.items;
  }

  get admins(): UserRecord[] {
    return this.items.filter((user) => user.roles.includes("admin"));
  }
}

export function normalizeRole(role: string): UserRole {
  const lowered = role.trim().toLowerCase();

  switch (lowered) {
    case "admin":
    case "editor":
      return lowered;
    default:
      return "viewer";
  }
}

export function createUser(id: number, name: string, roles: string[] = []): UserRecord {
  const normalize = (role: string): UserRole => normalizeRole(role);

  return {
    id,
    name: formatUserName(name),
    roles: roles.map(normalize),
    active: true,
  };
}

export async function fetchUser(id: number): Promise<UserRecord | null> {
  try {
    const response = await fetch(`/api/users/${id}`);

    if (!response.ok) {
      return null;
    }

    return await response.json();
  } catch (error) {
    console.error(`Unable to fetch ${formatUserName(String(id))}`, error);
    return null;
  }
}

export function summarizeUsers(users: UserRecord[]): UserSummary[] {
  const summaries: UserSummary[] = [];

  for (const user of users) {
    if (user.active === false) {
      continue;
    }

    summaries.push({
      id: user.id,
      label: `${formatUserName(user.name)}:${user.roles.join(",")}`,
      isAdmin: user.roles.includes("admin"),
    });
  }

  return summaries;
}

export function useUserSearch(initialUsers: UserRecord[]) {
  const [query, setQuery] = useState("");
  const [users, setUsers] = useState(initialUsers);

  useEffect(() => {
    let mounted = true;

    async function refreshUsers(): Promise<void> {
      const firstUser = await fetchUser(1);

      if (mounted && firstUser) {
        setUsers([firstUser, ...initialUsers]);
      }
    }

    refreshUsers();

    return () => {
      mounted = false;
    };
  }, [initialUsers]);

  const filtered = useMemo(
    () => users.filter((user) => user.name.toLowerCase().includes(query.toLowerCase())),
    [query, users],
  );

  return { query, setQuery, users: filtered };
}

type UserPanelProps = {
  initialUsers: UserRecord[];
  footer?: ReactNode;
};

export function UserPanel({ initialUsers, footer }: UserPanelProps) {
  const { query, setQuery, users } = useUserSearch(initialUsers);

  const renderUser = (user: UserRecord) => (
    <li key={user.id} data-admin={user.roles.includes("admin")}>
      {formatUserName(user.name)}
    </li>
  );

  return (
    <section>
      <input value={query} onChange={(event) => setQuery(event.target.value)} />
      <ul>{users.map((user) => renderUser(user))}</ul>
      {footer ?? <small>No footer</small>}
    </section>
  );
}

export function* iterateAdmins(users: UserRecord[]): Generator<UserRecord> {
  for (const user of users) {
    if (user.roles.includes("admin")) {
      yield user;
    }
  }
}

export function testCreateUser(): boolean {
  const user = createUser(1, "Ada", ["Admin"]);
  return user.roles.includes("admin");
}
