import { useCallback, useMemo } from "react";

// Desktop app is always authenticated with a desktop user
const DESKTOP_USER = {
  id: "desktop-user",
  name: "Desktop User",
  email: "desktop@hongtian.ai",
  role: "desktop",
};

type UseAuthOptions = {
  redirectOnUnauthenticated?: boolean;
  redirectPath?: string;
};

export function useAuth(options?: UseAuthOptions) {
  // Always return authenticated desktop user
  const user = DESKTOP_USER;
  const isAuthenticated = true;
  const isLoading = false;
  const error = null;

  const logout = useCallback(() => {
    // No-op for desktop app
    console.log("Logout is a no-op for desktop app");
  }, []);

  const refresh = useCallback(() => {
    // No-op for desktop app
    return Promise.resolve(DESKTOP_USER);
  }, []);

  return useMemo(
    () => ({
      user,
      isAuthenticated,
      isLoading,
      error,
      logout,
      refresh,
    }),
    [user, isAuthenticated, isLoading, error, logout, refresh],
  );
}