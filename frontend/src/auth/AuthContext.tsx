import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react"
import { api, clearToken, getToken, loginRequest, setToken } from "../api/client"
import type { User } from "../api/types"

interface AuthContextValue {
  user: User | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName: string) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  // Empieza en true si HAY token guardado: así ProtectedRoute no manda al
  // alumno a /login por un instante mientras se confirma la sesión de una
  // recarga de página — solo si el token resulta inválido lo redirige.
  const [isLoading, setIsLoading] = useState(() => getToken() !== null)

  const refreshUser = useCallback(async () => {
    if (!getToken()) {
      setUser(null)
      setIsLoading(false)
      return
    }
    try {
      const me = await api.get<User>("/auth/me")
      setUser(me)
    } catch {
      // Token caducado/inválido: lo limpiamos, que ProtectedRoute mande a /login.
      clearToken()
      setUser(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void refreshUser()
  }, [refreshUser])

  const login = useCallback(
    async (email: string, password: string) => {
      const { access_token } = await loginRequest(email, password)
      setToken(access_token)
      await refreshUser()
    },
    [refreshUser],
  )

  const register = useCallback(
    async (email: string, password: string, fullName: string) => {
      const { access_token } = await api.post<{ access_token: string }>("/auth/register", {
        email,
        password,
        full_name: fullName,
      })
      setToken(access_token)
      await refreshUser()
    },
    [refreshUser],
  )

  const logout = useCallback(() => {
    clearToken()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth() debe usarse dentro de <AuthProvider>.")
  return ctx
}
