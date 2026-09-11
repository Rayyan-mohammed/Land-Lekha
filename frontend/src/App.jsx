import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth'
import Layout from './components/Layout'
import { Spinner } from './components/ui'
import Audit from './pages/Audit'
import Dashboard from './pages/Dashboard'
import DocumentView from './pages/DocumentView'
import Documents from './pages/Documents'
import Login from './pages/Login'
import Records from './pages/Records'
import ReviewQueue from './pages/ReviewQueue'
import UploadPage from './pages/Upload'
import UsersPage from './pages/Users'

function Guard({ roles, children }) {
  const { can } = useAuth()
  return can(...roles) ? children : <Navigate to="/" replace />
}

export default function App() {
  const { user, ready } = useAuth()
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
      <Route path="audit" element={<Guard roles={[]}><Audit /></Guard>} />
      <Route path="users" element={<Guard roles={[]}><UsersPage /></Guard>} />
      <Route path="*" element={<Navigate to={home} replace />} />
    </Route>
  </Routes>
}
