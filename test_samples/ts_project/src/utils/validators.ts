import { PASSWORD_MIN_LENGTH } from "./constants";

const EMAIL_RE = /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/;

export function validateEmail(email: string): string | null {
  if (!email) return "Email is required";
  if (!EMAIL_RE.test(email)) return "Invalid email format";
  return null;
}

export function validateRequired(value: string, label = "Field"): string | null {
  if (!value || !value.trim()) return `${label} is required`;
  return null;
}

export function validatePassword(password: string): string | null {
  if (password.length < PASSWORD_MIN_LENGTH) {
    return `Password must be at least ${PASSWORD_MIN_LENGTH} characters`;
  }
  if (!/[A-Z]/.test(password)) return "Password must contain an uppercase letter";
  if (!/[0-9]/.test(password)) return "Password must contain a digit";
  return null;
}
