import { createContext, useContext, useEffect, useState } from 'react'
import { api, TOKEN_KEY } from '../api/client'

const AuthContext = createContext(null)
export const useAuth = () => useContext(AuthContext)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY))
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(!!token)

  // Récupère le profil au démarrage si un token est présent.
  useEffect(() => {
    if (!token) return
    api
      .get('/auth/me')
      .then((r) => setUser(r.data))
      .catch(() => logout())
      .finally(() => setLoading(false))
  }, []) // eslint-disable-line

  const persist = (data) => {
    localStorage.setItem(TOKEN_KEY, data.access_token)
    setToken(data.access_token)
    setUser(data.user)
    setLoading(false)
  }

  const login = async (email, password) => {
    const { data } = await api.post('/auth/login', { email, password })
    persist(data)
  }
  const register = async (payload) => {
    const { data } = await api.post('/auth/register', payload)
    persist(data)
  }
  const logout = () => {
    localStorage.removeItem(TOKEN_KEY)
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ token, user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
