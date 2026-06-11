export enum UserRole {
  ADMIN = "admin",
  USER = "user",
  GUEST = "guest",
}

export interface User {
  id: number;
  username: string;
  email: string;
  role: UserRole;
  isActive: boolean;
  createdAt: string;
  avatarUrl?: string;
}

export interface UserCredentials {
  email: string;
  password: string;
}

export interface CreateUserPayload {
  username: string;
  email: string;
  password: string;
  role?: UserRole;
}
