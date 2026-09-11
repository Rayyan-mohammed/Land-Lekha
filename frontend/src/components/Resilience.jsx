// Keep the app usable when something goes wrong: a crashed page shows a friendly
// message instead of a blank screen, and a lost connection is announced.
import { Component, useEffect, useState } from 'react'
import { RefreshCw, TriangleAlert, WifiOff } from 'lucide-react'
import { useT } from '../i18n'

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('page crashed', error, info?.componentStack)
  }

  render() {
    if (!this.state.error) return this.props.children
    // a class component cannot use the language hook; LangProvider keeps <html lang> current
    const hi = document.documentElement.lang === 'hi'
    return <div className="card mx-auto mt-10 max-w-lg p-6 text-center">
      <div className="mx-auto mb-3 w-fit rounded-full bg-amber-50 p-3 text-warn"><TriangleAlert size={26} /></div>
      <div className="font-medium text-slate-900">{hi ? 'इस पन्ने में कोई दिक़्क़त आ गई' : 'This page ran into a problem'}</div>
      <p className="mt-1 text-sm text-slate-600">{hi
        ? 'आपका सहेजा हुआ कुछ भी नहीं खोया। पन्ना फिर से खोलें; बार-बार हो तो प्रशासक को बताएँ कि आप क्या कर रहे थे।'
        : 'Nothing you saved is lost. Reload the page; if it keeps happening, tell the administrator what you were doing.'}</p>
      <button className="btn-primary mt-4" onClick={() => window.location.reload()}><RefreshCw size={16} /> {hi ? 'फिर से खोलें' : 'Reload'}</button>
      <details className="mt-4 text-left text-xs text-slate-500"><summary>{hi ? 'तकनीकी जानकारी' : 'Technical details'}</summary>
        <pre className="mt-2 whitespace-pre-wrap">{String(this.state.error?.message || this.state.error)}</pre></details>
    </div>
  }
}

export function OfflineBanner() {
  const { t } = useT()
  const [online, setOnline] = useState(() => navigator.onLine)
  useEffect(() => {
    const up = () => setOnline(true)
    const down = () => setOnline(false)
    window.addEventListener('online', up)
    window.addEventListener('offline', down)
    return () => { window.removeEventListener('online', up); window.removeEventListener('offline', down) }
  }, [])
  if (online) return null
  return <div role="alert" className="sticky top-0 z-30 flex items-center justify-center gap-2 bg-amber-100 px-4 py-2 text-sm font-medium text-amber-900 print:hidden">
    <WifiOff size={16} /> {t('You are offline. Uploads and approvals will not be saved until the connection returns.')}
  </div>
}
