import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import 'leaflet/dist/leaflet.css'
import './index.css'
import App from './App'
import { AuthProvider } from './auth'
import { ErrorBoundary } from './components/Resilience'
import { LangProvider } from './i18n'
import { ToastProvider } from './components/toast'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      {/* wraps everything, not just the authenticated layout in Layout.jsx, so a crash in
          Login, the public Verify page, or App's own routing shows the friendly crash page
          too instead of a blank screen */}
      <ErrorBoundary>
        <LangProvider>
          <AuthProvider>
            <ToastProvider>
              <App />
            </ToastProvider>
          </AuthProvider>
        </LangProvider>
      </ErrorBoundary>
    </BrowserRouter>
  </StrictMode>,
)
