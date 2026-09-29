"use client";

import { useEffect, useState } from "react";

export interface User {
  id: string;
  email: string;
  full_name?: string | null;
  is_active?: boolean;
}

const TOKEN_KEY = "autoapply_access_token";
const USER_KEY = "autoapply_user";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setAuth(token: string, user?: User | null) {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, token);
  if (user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }
  // Dispatch custom event for reactive tab/component updates
  window.dispatchEvent(new Event("autoapply_auth_change"));
}

export function clearAuth() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  window.dispatchEvent(new Event("autoapply_auth_change"));
}

export function getStoredUser(): User | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    function sync() {
      setToken(getAccessToken());
      setUser(getStoredUser());
      setIsLoading(false);
    }

    sync();
    window.addEventListener("autoapply_auth_change", sync);
    window.addEventListener("storage", sync);

    return () => {
      window.removeEventListener("autoapply_auth_change", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  return {
    user,
    token,
    isAuthenticated: Boolean(token),
    isLoading,
    logout: () => {
      clearAuth();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    },
  };
}
