import { lazy } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth } from './auth'
import Layout from './components/Layout'
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

export default function App() {
  const { user, ready } = useAuth()
  const location = useLocation()
  // the QR code on a printed extract opens this page: it must work without logging in
  if (location.pathname.startsWith('/verify/')) return <Routes><Route path="/verify/:id" element={<Verify />} /></Routes>
  if (!ready) return <div className="flex h-full items-center justify-center"><Spinner /></div>
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
