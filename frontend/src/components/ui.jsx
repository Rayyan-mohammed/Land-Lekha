import { useEffect, useState } from 'react'
import { STATUS } from '../constants'

export function StatusBadge({ status }) {
  const s = STATUS[status] || { label: status, cls: 'bg-slate-100 text-slate-700' }
  return <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${s.cls}`}>
    {(status === 'processing' || status === 'queued') && <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse" />}
    {s.label}
  </span>
}

export function confColor(c, threshold = 0.8) {
  if (c == null) return 'text-slate-400'
  if (c >= threshold) return 'text-ok'
  if (c >= threshold - 0.2) return 'text-warn'
  return 'text-bad'
}

export function ConfidenceBar({ value, threshold = 0.8, className = '' }) {
  if (value == null) return <span className="text-xs text-slate-400">—</span>
  const pct = Math.round(value * 100)
  const bar = value >= threshold ? 'bg-ok' : value >= threshold - 0.2 ? 'bg-warn' : 'bg-bad'
  return <div className={`flex items-center gap-2 ${className}`} title={`confidence ${pct}% (auto-accept at ${Math.round(threshold * 100)}%)`}>
    <div className="relative h-1.5 w-16 rounded-full bg-slate-200 overflow-hidden">
      <div className={`absolute inset-y-0 left-0 ${bar}`} style={{ width: `${pct}%` }} />
    </div>
    <span className={`text-xs tabular-nums font-medium ${confColor(value, threshold)}`}>{pct}%</span>
  </div>
}

export function Stat({ label, value, sub, icon: Icon, tone = 'brand' }) {
  const tones = { brand: 'bg-brand-50 text-brand-700', ok: 'bg-emerald-50 text-emerald-700', warn: 'bg-amber-50 text-amber-700', bad: 'bg-red-50 text-red-700', slate: 'bg-slate-100 text-slate-700' }
  return <div className="card p-4 flex items-start gap-3">
    {Icon && <div className={`rounded-lg p-2 ${tones[tone]}`}><Icon size={18} /></div>}
    <div className="min-w-0">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="text-2xl font-semibold tabular-nums text-slate-900">{value ?? '—'}</div>
      {sub && <div className="text-xs text-slate-500 mt-0.5">{sub}</div>}
    </div>
  </div>
}

export function PageHeader({ title, subtitle, actions }) {
  return <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
    <div>
      <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
      {subtitle && <p className="text-sm text-slate-500 mt-0.5">{subtitle}</p>}
    </div>
    {actions && <div className="flex gap-2">{actions}</div>}
  </div>
}

export function ErrorNote({ error }) {
  if (!error) return null
  return <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{String(error.message || error)}</div>
}

export function Spinner({ className = '' }) {
  return <div className={`h-5 w-5 animate-spin rounded-full border-2 border-brand-200 border-t-brand-700 ${className}`} />
}

export function Empty({ children }) {
  return <div className="py-12 text-center text-sm text-slate-500">{children}</div>
}

// Loads an authenticated image (Authorization header) as an object URL.
export function useAuthImage(loader, deps) {
  const [url, setUrl] = useState(null)
  useEffect(() => {
    let alive = true
    let obj
    setUrl(null)
    loader().then((blob) => {
      if (!alive) return
      obj = URL.createObjectURL(blob)
      setUrl(obj)
    }).catch(() => {})
    return () => { alive = false; if (obj) URL.revokeObjectURL(obj) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  return url
}

export function fmtDate(s) {
  if (!s) return '—'
  const d = new Date(s)
  return d.toLocaleString(undefined, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}
