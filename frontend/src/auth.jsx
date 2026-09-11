import { createContext, useContext, useEffect, useState } from 'react'
import { api, getToken, setToken } from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    if (!getToken()) return setReady(true)
    api.me().then(setUser).catch(() => setToken(null)).finally(() => setReady(true))
  }, [])

  useEffect(() => {
    const onLogout = () => setUser(null)
    window.addEventListener('landlekha:logout', onLogout)
    return () => window.removeEventListener('landlekha:logout', onLogout)
  }, [])

  const login = async (username, password) => {
    const res = await api.login(username, password)
    setToken(res.access_token)
    setUser(res.user)
    return res.user
  }
  const logout = () => {
    setToken(null)
    setUser(null)
  }
  const can = (...roles) => !!user && (user.role === 'admin' || roles.includes(user.role))

  return <AuthContext.Provider value={{ user, ready, login, logout, can }}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
