import React from "react";

export interface ButtonProps {
  label: string;
  onClick: () => void;
  variant?: "primary" | "secondary" | "danger";
  disabled?: boolean;
  isLoading?: boolean;
  type?: "button" | "submit" | "reset";
}

export function Button({ label, onClick, variant = "primary", disabled, isLoading, type = "button" }: ButtonProps) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || isLoading}
      className={`btn btn-${variant}`}
    >
      {isLoading ? "Loading…" : label}
    </button>
  );
}

export default Button;
