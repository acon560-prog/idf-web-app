import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import { buildApiUrl } from "../utils/apiConfig";

const AuthContext = createContext();

export function AuthProvider({ children }) {
   const [user, setUser] = useState(
    () => JSON.parse(localStorage.getItem("user")) || null,
  );
  const [token, setToken] = useState(
    () => localStorage.getItem("accessToken") || null,
  );
  const [refreshToken, setRefreshToken] = useState(
    () => localStorage.getItem("refreshToken") || null,
  );

  const setSession = useCallback((userData, accessToken, newRefreshToken) => {
    setUser(userData);
    setToken(accessToken);
    setRefreshToken(newRefreshToken || null);
    if (userData) {
      localStorage.setItem("user", JSON.stringify(userData));
    } else {
      localStorage.removeItem("user");
    }
    if (accessToken) {
      localStorage.setItem("accessToken", accessToken);
    } else {
       localStorage.removeItem("accessToken");
    }
    if (newRefreshToken) {
      localStorage.setItem("refreshToken", newRefreshToken);
    } else if (!newRefreshToken) {
      localStorage.removeItem("refreshToken");
    }
  }, []);
  
  const logout = useCallback(() => {
    setSession(null, null, null);
  }, [setSession]);

  const refreshAccessToken = useCallback(async () => {
    if (!refreshToken) {
      logout();
      return null;
    }
    try {
       const res = await fetch(buildApiUrl("/auth/refresh-token"), {
        method: "POST",
        headers: {
          Authorization: `Bearer ${refreshToken}`,
        },  
      });

      if (res.ok) {
        const data = await res.json();
        if (!data.accessToken) {
          throw new Error("Missing access token in refresh response");
        }
        setToken(data.accessToken);
        localStorage.setItem("accessToken", data.accessToken);
        return data.accessToken;
      } else {
        logout();
        return null;
      }
    } catch (err) {
      console.error('Refresh token error:', err);
      logout();
      return null;
    }
  }, [refreshToken, logout]);

  // Auto-refresh token shortly before expiry (optional)
  useEffect(() => {
    if (!token) return;

    const parseJwt = (jwt) => {
      try {
        return JSON.parse(atob(jwt.split(".")[1]));
      } catch {
        return null;
      }
    };

    const payload = parseJwt(token);
    if (!payload || !payload.exp) return;

    const expiresInMs = payload.exp * 1000 - Date.now();
    const timeoutId = setTimeout(() => {
      refreshAccessToken();
    }, expiresInMs - 60000);

    return () => clearTimeout(timeoutId);
  }, [token, refreshAccessToken]);

  // Wrapper around fetch for authenticated calls with auto-refresh
   const authFetch = useCallback(
    async (url, options = {}) => {
      let headers = options.headers ? { ...options.headers } : {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

        let res = await fetch(url, { ...options, headers });
          if (res.status === 401) {
            const newToken = await refreshAccessToken();
            if (newToken) {
              headers["Authorization"] = `Bearer ${newToken}`;
              res = await fetch(url, { ...options, headers });
            } else {
              logout();
            }
          }
          return res;
        },
        [token, refreshAccessToken, logout],
      );

     const syncProfile = useCallback(
      async (overrideToken) => {
        const activeToken = overrideToken || token;
        if (!activeToken) return null;

        try {
            const res = await fetch(buildApiUrl("/auth/me"), {
              headers: {
                Authorization: `Bearer ${activeToken}`,
              },
            });

            if (res.ok) {
                const data = await res.json();
                if (data?.user) {
                  setUser(data.user);
                  localStorage.setItem("user", JSON.stringify(data.user));
                }
                return data?.user ?? null;
              }

                if (res.status === 401) {
                    const newToken = await refreshAccessToken();
                    if (newToken && newToken !== activeToken) {
                      return syncProfile(newToken);
                    }
                    logout();
                  }
                } catch (err) {
                  console.error("Failed to sync user profile", err);
                }

    return null;
    },
    [token, refreshAccessToken, logout],
  );

  useEffect(() => {
    if (!token) return;
    syncProfile(token);
  }, [token, syncProfile]);

  const login = useCallback(
    (userData, accessToken, newRefreshToken) => {
      setSession(userData, accessToken, newRefreshToken);
    },
    [setSession],
  );

  return (
    <AuthContext.Provider
      value={{ user, token, refreshToken, login, logout, authFetch }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}