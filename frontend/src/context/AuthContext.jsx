import { createContext, useContext, useState, useEffect } from "react";
import { thiqaApi } from "../api/thiqa";

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Check if user is already logged in on app start
  useEffect(() => {
    const token = localStorage.getItem("thiqa_token");
    if (token) {
      thiqaApi.me()
        .then((data) => setUser(data))
        .catch(() => {
          localStorage.removeItem("thiqa_token");
          setUser(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  async function login(email, password) {
    const data = await thiqaApi.login(email, password);
    localStorage.setItem("thiqa_token", data.token);
    const me = await thiqaApi.me();
    setUser(me);
    return me;
  }

  async function register(firstName, lastName, email, password) {
    const data = await thiqaApi.register(email, password);
    localStorage.setItem("thiqa_token", data.token);
    const me = await thiqaApi.me();
    setUser(me);
    return me;
  }

  async function logout() {
    try { await thiqaApi.logout(); } catch (_) {}
    localStorage.removeItem("thiqa_token");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, register, loading }}>
      {!loading && children}
    </AuthContext.Provider>
  );
}

export function useAuth() { return useContext(AuthContext); }