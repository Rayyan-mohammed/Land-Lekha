import { createContext, useContext, useEffect, useState } from 'react'
import { api, getToken, setToken } from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)
  const [offline, setOffline] = useState(false)  // the server could not be reached, token still valid

  // a rejected token signs the user out; an unreachable server does not (the backend may be restarting)
  const check = () => {
    setReady(false)
    return api.me()
      .then((u) => { setUser(u); setOffline(false) })
      .catch((e) => { if (e.status === 0) setOffline(true); else setToken(null) })
      .finally(() => setReady(true))
  }

  useEffect(() => {
    if (!getToken()) return setReady(true)
    check()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const onLogout = () => setUser(null)
    window.addEventListener('landlekha:logout', onLogout)
    return () => window.removeEventListener('landlekha:logout', onLogout)
  }, [])

  const login = async (username, password) => {
    const res = await api.login(username, password)
    setToken(res.access_token)
    setUser(res.user)
    setOffline(false)
    return res.user
  }
  const logout = () => {
    setToken(null)
    setUser(null)
  }
  const can = (...roles) => !!user && (user.role === 'admin' || roles.includes(user.role))

  return <AuthContext.Provider value={{ user, ready, offline, retry: check, login, logout, can }}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
