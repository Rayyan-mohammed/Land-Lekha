import { lazy, useEffect } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth } from './auth'
import Layout from './components/Layout'
import { ServerDown } from './components/Resilience'
import { Spinner } from './components/ui'
import Login from './pages/Login'
import Verify from './pages/Verify'

// Each screen is its own chunk: the charts (dashboard), the map (records) and the QR code
// (extract) download only when someone opens that screen, so sign-in stays fast on slow links.
const Audit = lazy(() => import('./pages/Audit'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const DocumentView = lazy(() => import('./pages/DocumentView'))
const Documents = lazy(() => import('./pages/Documents'))
const Extract = lazy(() => import('./pages/Extract'))
const Help = lazy(() => import('./pages/Help'))
const Records = lazy(() => import('./pages/Records'))
const ReviewQueue = lazy(() => import('./pages/ReviewQueue'))
const UploadPage = lazy(() => import('./pages/Upload'))
const UsersPage = lazy(() => import('./pages/Users'))

function Guard({ roles, children }) {
  const { can } = useAuth()
  return can(...roles) ? children : <Navigate to="/" replace />
}

// Screens are loaded per route, so the first visit to each one waits for its chunk. Tehsil
// offices are often on a slow line, so once the app is idle we fetch the screens this person
// will actually open next, in the order they usually open them.
const NEXT_SCREENS = {
  operator: [() => import('./pages/Documents'), () => import('./pages/DocumentView'), () => import('./pages/Records')],
  verifier: [() => import('./pages/DocumentView'), () => import('./pages/Documents'), () => import('./pages/Dashboard'), () => import('./pages/Records')],
  admin: [() => import('./pages/Records'), () => import('./pages/Documents'), () => import('./pages/Audit')],
}

function usePrefetch(role) {
  useEffect(() => {
    if (!role || navigator.connection?.saveData) return   // respect "data saver"
    let cancelled = false
    const load = async () => {
      for (const screen of NEXT_SCREENS[role] || []) {
        if (cancelled) return
        try { await screen() } catch { return }           // offline: the route will load it later
      }
    }
    const idle = window.requestIdleCallback || ((fn) => setTimeout(fn, 1500))
    const id = idle(load, { timeout: 4000 })
    return () => { cancelled = true; window.cancelIdleCallback?.(id) }
  }, [role])
}

export default function App() {
  const { user, ready, offline, retry } = useAuth()
  const location = useLocation()
  usePrefetch(user?.role)
  // the QR code on a printed extract opens this page: it must work without logging in
  if (location.pathname.startsWith('/verify/')) return <Routes><Route path="/verify/:id" element={<Verify />} /></Routes>
  if (!ready) return <div className="flex h-full items-center justify-center"><Spinner /></div>
  if (offline && !user) return <ServerDown onRetry={retry} />
  if (!user) return <Login />
  const home = user.role === 'operator' ? '/upload' : user.role === 'verifier' ? '/review' : '/dashboard'
  return <Routes>
    <Route element={<Layout />}>
      <Route index element={<Navigate to={home} replace />} />
      <Route path="upload" element={<Guard roles={['operator', 'verifier']}><UploadPage /></Guard>} />
      <Route path="documents" element={<Documents />} />
      <Route path="documents/:id" element={<DocumentView />} />
      <Route path="review" element={<Guard roles={['verifier']}><ReviewQueue /></Guard>} />
      <Route path="dashboard" element={<Guard roles={['verifier']}><Dashboard /></Guard>} />
      <Route path="records" element={<Records />} />
      <Route path="records/:id/extract" element={<Extract />} />
      <Route path="help" element={<Help />} />
      <Route path="audit" element={<Guard roles={[]}><Audit /></Guard>} />
      <Route path="users" element={<Guard roles={[]}><UsersPage /></Guard>} />
      <Route path="*" element={<Navigate to={home} replace />} />
    </Route>
  </Routes>
}
