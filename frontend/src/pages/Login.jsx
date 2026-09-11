import { useEffect, useState } from 'react'
import { BarChart3, ClipboardCheck, Clock, FileUp, ScanText, ShieldCheck, Upload } from 'lucide-react'
import { useAuth } from '../auth'
import { Logo } from '../components/Layout'
import { ErrorNote } from '../components/ui'
import { LangToggle, useT } from '../i18n'

const DEMO = [
  ['operator', 'upload@123', 'Field operator', 'uploads records from the counter or a phone', Upload],
  ['verifier', 'verify@123', 'Tehsil verifier', 'checks only the fields the system is unsure of', ClipboardCheck],
  ['admin', 'admin@123', 'Administrator', 'dashboards, users and the audit trail', BarChart3],
]

const STEPS = [
  [FileUp, 'Upload', 'A scan, a PDF or a phone photo of a Khatauni, Jamabandi or Record of Rights.'],
  [ScanText, 'Read and check', 'Hindi and English text is read, every field is checked against rules and master data.'],
  [ShieldCheck, 'Verify', 'Confident records go straight through. A verifier looks only at what is flagged.'],
]

// Faint cadastral-map pattern: irregular parcel boundaries, like a village map sheet.
function ParcelPattern() {
  return <svg className="pointer-events-none absolute inset-0 h-full w-full opacity-[0.09]" aria-hidden>
    <defs>
      <pattern id="parcels" width="220" height="180" patternUnits="userSpaceOnUse">
        <path d="M0 40 L70 28 L96 90 L30 118 Z M70 28 L150 0 L176 70 L96 90 Z M150 0 L220 20 L210 96 L176 70 Z M30 118 L96 90 L120 170 L20 180 Z M96 90 L176 70 L200 150 L120 170 Z M176 70 L210 96 L220 180 L200 150 Z"
          fill="none" stroke="#f2c14e" strokeWidth="1.2" />
      </pattern>
    </defs>
    <rect width="100%" height="100%" fill="url(#parcels)" />
  </svg>
}

export default function Login() {
  const { t } = useT()
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  // set by api.js when the server rejected an expired token; the URL is unchanged, so signing
  // in again returns the user to the page they were on
  const [expired] = useState(() => { try { return sessionStorage.getItem('landlekha.expired') === '1' } catch { return false } })
  useEffect(() => { try { sessionStorage.removeItem('landlekha.expired') } catch { /* storage blocked */ } }, [])
  useEffect(() => { document.title = `${t('Sign in')} · LandLekha` }, [t])

  const signIn = async (u, p) => {
    setBusy(true)
    setError(null)
    try { await login(u, p) } catch (err) { setError(err) } finally { setBusy(false) }
  }
  const submit = (e) => { e.preventDefault(); signIn(username, password) }

  return <div className="grid min-h-full lg:grid-cols-[1.1fr_1fr]">
    <div className="relative hidden flex-col justify-between overflow-hidden bg-brand-800 p-10 text-white lg:flex">
      <ParcelPattern />
      <div className="pointer-events-none absolute -right-24 -top-24 h-80 w-80 rounded-full bg-accent/10 blur-3xl" aria-hidden />
      <div className="relative"><Logo light /></div>
      <div className="relative max-w-lg">
        <h2 className="text-3xl font-semibold leading-tight">From handwritten registers to verified digital land records.</h2>
        <p className="mt-2 text-xl text-accent">हस्तलिखित रजिस्टर से सत्यापित डिजिटल भूमि अभिलेख तक</p>
        <ol className="mt-8 space-y-4">
          {STEPS.map(([Icon, title, text], i) => <li key={title} className="flex gap-4">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/10 ring-1 ring-white/15"><Icon size={19} /></div>
            <div><div className="font-medium"><span className="mr-1.5 text-accent">{i + 1}.</span>{t(title)}</div>
              <div className="text-sm text-brand-100">{t(text)}</div></div>
          </li>)}
        </ol>
      </div>
      <div className="relative flex flex-wrap gap-x-4 gap-y-1 text-xs text-brand-200">
        <span>SIH 2026 · PS 26018</span><span>Department of Land Resources, MoRD</span><span>Hindi · English</span>
      </div>
    </div>

    <div className="flex min-w-0 flex-col">
      <div className="relative overflow-hidden bg-brand-800 px-6 py-5 text-white lg:hidden">
        <ParcelPattern />
        <div className="relative"><Logo light /></div>
        <p className="relative mt-3 text-sm text-brand-100">{t('From handwritten registers to verified digital land records.')}</p>
      </div>
      <main className="flex flex-1 items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-semibold text-slate-900">{t('Sign in')}</h1>
            <LangToggle className="border-slate-300 text-slate-700" />
          </div>
          <p className="mt-1 text-sm text-slate-600">{t('Use your department account.')}</p>
          {expired && <div role="status" className="mt-4 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            <Clock size={16} className="mt-0.5 shrink-0" /> {t('Your session has ended. Sign in again to carry on where you left off.')}</div>}
          <form onSubmit={submit} className="mt-6 space-y-4">
            <div><label className="label" htmlFor="u">{t('Username')}</label>
              <input id="u" className="input" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" autoFocus /></div>
            <div><label className="label" htmlFor="p">{t('Password')}</label>
              <input id="p" type="password" className="input" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" /></div>
            <ErrorNote error={error} />
            <button className="btn-primary w-full" disabled={busy || !username || !password}>
              <ShieldCheck size={16} /> {busy ? t('Signing in…') : t('Sign in')}</button>
          </form>

          <div className="mt-8">
            <div className="label">{t('Demo accounts')}</div>
            <div className="grid gap-2">
              {DEMO.map(([u, p, role, what, Icon]) => (
                <button key={u} type="button" disabled={busy} onClick={() => { setUsername(u); setPassword(p); signIn(u, p) }}
                  className="group flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 text-left transition-colors duration-200 hover:border-brand-500 hover:bg-brand-50">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-700 group-hover:bg-white"><Icon size={17} /></div>
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-slate-900">{t(role)} <span className="font-normal text-slate-500">· {u}</span></div>
                    <div className="truncate text-xs text-slate-600">{t(what)}</div>
                  </div>
                </button>
              ))}
            </div>
            <p className="mt-2 text-xs text-slate-500">{t('Demo only: one click signs in. Real deployments turn these accounts off.')}</p>
          </div>
        </div>
      </main>
    </div>
  </div>
}
