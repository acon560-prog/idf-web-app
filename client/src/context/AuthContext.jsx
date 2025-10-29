import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem('user')) || null);
  const [token, setToken] = useState(() => localStorage.getItem('accessToken') || null);
  const [refreshToken, setRefreshToken] = useState(() => localStorage.getItem('refreshToken') || null);

  const logout = useCallback(() => {
    setUser(null);
    setToken(null);
    setRefreshToken(null);
    localStorage.removeItem('user');
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
  }, []);

  const refreshAccessToken = useCallback(async () => {
    if (!refreshToken) {
      logout();
      return null;
    }
    try {
      const res = await fetch(`${process.env.REACT_APP_API_BASE_URL}/api/auth/refresh-token`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        //headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: refreshToken }),
      });

      if (res.ok) {
        const data = await res.json();
        setToken(data.accessToken);
        localStorage.setItem('accessToken', data.accessToken);

        if (data.refreshToken) {
          setRefreshToken(data.refreshToken);
          localStorage.setItem('refreshToken', data.refreshToken);
        }
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
        return JSON.parse(atob(jwt.split('.')[1]));
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
  const authFetch = useCallback(async (url, options = {}) => {
   const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000';

  // Prepend base URL if url is relative
  if (!url.startsWith('http')) {
    url = `${API_BASE_URL}${url.startsWith('/') ? '' : '/'}${url}`;
  }
    let headers = options.headers ? { ...options.headers } : {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    let res = await fetch(url, { ...options, headers });
    if (res.status === 401) {
      const newToken = await refreshAccessToken();
      if (newToken) {
        headers['Authorization'] = `Bearer ${newToken}`;
        res = await fetch(url, { ...options, headers });
      } else {
        logout();
      }
    }
    return res;
  }, [token, refreshAccessToken, logout]);

const login = async (username, password) => {
  const url = `${process.env.REACT_APP_API_BASE_URL}/api/login`;
  console.log("Login URL:", url);  // Log the full URL here
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      
      body: JSON.stringify({ username, password }),
    });

    if (!res.ok) return false;

    const data = await res.json();
    // data should contain user info, accessToken, refreshToken
    setUser(data.user);
    setToken(data.token);
    //setRefreshToken(data.refreshToken);
    localStorage.setItem('user', JSON.stringify(data.user));
    localStorage.setItem('accessToken', data.accessToken);
    localStorage.setItem('refreshToken', data.refreshToken);
    return true;
  } catch (err) {
    console.error('Login error:', err);
    return false;
  }
};

  return (
    <AuthContext.Provider value={{ user, token, refreshToken, login, logout, authFetch }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
