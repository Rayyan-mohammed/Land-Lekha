import { useEffect, useState } from 'react'
import { STATUS } from '../constants'
import { useT } from '../i18n'

export function StatusBadge({ status }) {
  const { t } = useT()
  const s = STATUS[status] || { label: status, cls: 'bg-slate-100 text-slate-700' }
  return <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${s.cls}`}>
    {(status === 'processing' || status === 'queued') && <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse" />}
    {t(s.label)}
  </span>
}

const QUALITY = {
  good: { label: 'Good image', cls: 'bg-emerald-100 text-emerald-800' },
  fair: { label: 'Fair image', cls: 'bg-amber-100 text-amber-800' },
  poor: { label: 'Poor image — retake', cls: 'bg-red-100 text-red-800' },
}

export function QualityBadge({ quality }) {
  const { t } = useT()
  if (!quality) return null
  const q = QUALITY[quality.verdict] || { label: quality.verdict, cls: 'bg-slate-100 text-slate-700' }
  return <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium ${q.cls}`}
    title={`median OCR confidence ${Math.round((quality.median_confidence || 0) * 100)}%, sharpness ${quality.sharpness}`}>{t(q.label)}</span>
}

// the worst page decides what the operator is told
export function worstQuality(pages = []) {
  const order = { poor: 0, fair: 1, good: 2 }
  return pages.map((p) => p.quality).filter(Boolean).sort((a, b) => order[a.verdict] - order[b.verdict])[0] || null
}

export function confColor(c, threshold = 0.8) {
  if (c == null) return 'text-slate-500'
  if (c >= threshold) return 'text-ok'
  if (c >= threshold - 0.2) return 'text-warn'
  return 'text-bad'
}

export function ConfidenceBar({ value, threshold = 0.8, className = '' }) {
  if (value == null) return <span className="text-xs text-slate-500">—</span>
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
  const { t } = useT()
  if (!error) return null
  // status 0 means the request never reached the server; say that plainly instead of "Failed to fetch"
  const text = error.status === 0 ? t('Could not reach the server. Check that it is running, then try again.')
    : String(error.message || error)
  return <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{text}</div>
}

export function Spinner({ className = '' }) {
  return <div className={`h-5 w-5 animate-spin rounded-full border-2 border-brand-200 border-t-brand-700 ${className}`} />
}

export function Empty({ children }) {
  return <div className="py-12 text-center text-sm text-slate-500">{children}</div>
}

// Friendly empty screen: an icon, what it means, and what to do next.
export function EmptyState({ icon: Icon, title, children, action, tone = 'brand' }) {
  const tones = { brand: 'bg-brand-50 text-brand-600', ok: 'bg-emerald-50 text-ok' }
  return <div className="flex flex-col items-center px-6 py-14 text-center">
    {Icon && <div className={`mb-3 rounded-full p-3 ${tones[tone]}`}><Icon size={26} /></div>}
    <div className="font-medium text-slate-900">{title}</div>
    {children && <div className="mt-1 max-w-md text-sm text-slate-600">{children}</div>}
    {action && <div className="mt-4">{action}</div>}
  </div>
}

// Placeholder rows while a table loads, so the layout doesn't jump.
export function SkeletonRows({ rows = 6, cols = 5 }) {
  return <div className="divide-y divide-slate-100" aria-busy="true" aria-label="loading">
    {Array.from({ length: rows }, (_, r) => <div key={r} className="flex items-center gap-4 px-4 py-3.5">
      {Array.from({ length: cols }, (_, c) => <div key={c} className="h-3 animate-pulse rounded bg-slate-200"
        style={{ width: `${c === 1 ? 28 : 10 + ((r * 7 + c * 13) % 14)}%` }} />)}
    </div>)}
  </div>
}

export function SkeletonCards({ n = 4 }) {
  return <div className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-busy="true" aria-label="loading">
    {Array.from({ length: n }, (_, i) => <div key={i} className="card p-4">
      <div className="h-3 w-24 animate-pulse rounded bg-slate-200" />
      <div className="mt-3 h-6 w-16 animate-pulse rounded bg-slate-200" />
      <div className="mt-2 h-2.5 w-32 animate-pulse rounded bg-slate-100" />
    </div>)}
  </div>
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

// The API stores times in UTC; SQLite drops the zone, so a bare "2026-09-11T16:25:00" is UTC, not local.
export function parseTs(s) {
  if (!s) return null
  return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(s) ? s : `${s}Z`)
}

// dates follow the language chosen in the app (LangProvider sets <html lang>), not the browser's
export const locale = () => (document.documentElement.lang === 'hi' ? 'hi-IN' : 'en-IN')

export function fmtDate(s) {
  if (!s) return '—'
  const d = parseTs(s)
  return d.toLocaleString(locale(), { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}
