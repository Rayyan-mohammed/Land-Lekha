// Small, self-dismissing confirmations ("Record approved", "Pushed to LRMS").
// Rendered in an aria-live region so screen readers announce them too.
import { createContext, useCallback, useContext, useRef, useState } from 'react'
import { AlertTriangle, CheckCircle2, Info, X } from 'lucide-react'
import { useT } from '../i18n'

const ToastContext = createContext({ toast: () => {} })
const STYLES = {
  success: { icon: CheckCircle2, cls: 'border-emerald-200 bg-white', iconCls: 'text-ok' },
  error: { icon: AlertTriangle, cls: 'border-red-200 bg-white', iconCls: 'text-bad' },
  info: { icon: Info, cls: 'border-slate-200 bg-white', iconCls: 'text-brand-600' },
}

export function ToastProvider({ children }) {
  const { t: tr } = useT()   // `t` is a toast in the list below
  const [items, setItems] = useState([])
  const seq = useRef(0)
  const dismiss = useCallback((id) => setItems((xs) => xs.filter((x) => x.id !== id)), [])
  const toast = useCallback((title, { type = 'success', body, ms = 4000 } = {}) => {
    const id = ++seq.current
    setItems((xs) => [...xs.slice(-3), { id, title, body, type }])
    if (ms) setTimeout(() => dismiss(id), type === 'error' ? ms * 2 : ms)
  }, [dismiss])

  return <ToastContext.Provider value={{ toast }}>
    {children}
    <div aria-live="polite" role="status" className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-2 print:hidden">
      {items.map((t) => {
        const s = STYLES[t.type] || STYLES.info
        const Icon = s.icon
        return <div key={t.id} className={`animate-rise pointer-events-auto flex items-start gap-3 rounded-xl border p-3 shadow-lg ${s.cls}`}>
          <Icon size={18} className={`mt-0.5 shrink-0 ${s.iconCls}`} />
          <div className="min-w-0 flex-1">
            <div className="text-sm font-medium text-slate-900">{t.title}</div>
            {t.body && <div className="mt-0.5 text-xs text-slate-600">{t.body}</div>}
          </div>
          <button onClick={() => dismiss(t.id)} aria-label={tr('Dismiss')} className="rounded p-0.5 text-slate-500 hover:bg-slate-100"><X size={14} /></button>
        </div>
      })}
    </div>
  </ToastContext.Provider>
}

export const useToast = () => useContext(ToastContext).toast
