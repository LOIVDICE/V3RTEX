import React, { useEffect, useMemo, useState } from "react";
import { formatUserName as formatName } from "./formatters";

const legacyLogger = require("./legacyLogger");
const DEFAULT_LIMIT = 20;

export class UserStore {
  constructor(seedUsers = []) {
    this.users = seedUsers;
  }

  get activeUsers() {
    return this.users.filter((user) => user.active);
  }

  addUser(user) {
    if (!user || !user.id) {
      throw new Error(`Invalid user: ${formatName(user?.name || "unknown")}`);
    }

    this.users.push(user);
    return this;
  }

  *admins() {
    for (const user of this.users) {
      if (user.roles?.includes("admin")) {
        yield user;
      }
    }
  }
}

export function createUser(id, name, roles = []) {
  const normalize = (value) => value.trim().toLowerCase();
  const normalizedRoles = roles.map((role) => normalize(role));

  return {
    id,
    name: formatName(name),
    roles: normalizedRoles,
    active: true,
  };
}

export async function loadRemoteUsers(endpoint = "/api/users") {
  try {
    const response = await fetch(endpoint);

    if (!response.ok) {
      return [];
    }

    return await response.json();
  } catch (error) {
    legacyLogger.warn(`Failed loading users: ${error.message}`);
    return [];
  }
}

export async function loadFormatter(pluginName) {
  const module = await import(`./plugins/${pluginName}.js`);
  return module.default;
}

export function buildUserIndex(users) {
  const index = new Map();

  for (const user of users) {
    if (!user.active) {
      continue;
    }

    index.set(user.id, user);
  }

  return index;
}

export function summarizeUsers(users, limit = DEFAULT_LIMIT) {
  let count = 0;
  const names = [];

  while (count < users.length && count < limit) {
    const user = users[count];

    if (user.active ? user.roles.length > 0 : false) {
      names.push(`${formatName(user.name)}:${user.roles.join(",")}`);
    }

    count += 1;
  }

  return names.join("|");
}

export function useUsers(initialUsers = []) {
  const [users, setUsers] = useState(initialUsers);

  useEffect(() => {
    let cancelled = false;

    async function refresh() {
      const remoteUsers = await loadRemoteUsers();

      if (!cancelled) {
        setUsers(remoteUsers);
      }
    }

    refresh();

    return () => {
      cancelled = true;
    };
  }, []);

  return users;
}

export default function UserList({ initialUsers = [] }) {
  const users = useUsers(initialUsers);
  const visibleUsers = useMemo(() => users.filter((user) => user.active), [users]);

  function renderUser(user) {
    return (
      <li key={user.id} data-admin={user.roles.includes("admin")}>
        {formatName(user.name)}
      </li>
    );
  }

  return (
    <>
      <h2>Users</h2>
      <ul>{visibleUsers.map((user) => renderUser(user))}</ul>
    </>
  );
}

export function testBuildUserIndex() {
  const user = createUser(1, "Ada", ["Admin"]);
  const index = buildUserIndex([user]);
  return index.has(1);
}
