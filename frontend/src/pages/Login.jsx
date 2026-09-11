import { useState } from 'react'
import { ShieldCheck } from 'lucide-react'
import { useAuth } from '../auth'
import { Logo } from '../components/Layout'
import { ErrorNote } from '../components/ui'

const DEMO = [
  ['operator', 'upload@123', 'Field operator — uploads records'],
  ['verifier', 'verify@123', 'Tehsil verifier — reviews flagged fields'],
  ['admin', 'admin@123', 'Administrator — dashboards, users, audit'],
]

export default function Login() {
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try { await login(username, password) } catch (err) { setError(err) } finally { setBusy(false) }
  }

  return <div className="min-h-full grid lg:grid-cols-2">
    <div className="hidden lg:flex flex-col justify-between bg-brand-800 p-10 text-white">
      <Logo light />
      <div>
        <h2 className="text-3xl font-semibold leading-tight">From handwritten registers to verified digital land records.</h2>
        <p className="mt-4 text-brand-100 max-w-md">Upload a scanned Khatauni, Jamabandi or Record of Rights — in Hindi or English, printed or handwritten.
          LandLekha reads it, checks every field against format rules and master data, and only asks a human about what it isn't sure of.</p>
        <ul className="mt-8 space-y-2 text-sm text-brand-100">
          <li>• OCR + computer vision for degraded scans and phone photos</li>
          <li>• Calibrated confidence on every field, human-in-the-loop review</li>
          <li>• Audit trail, role-based access, LRMS / DILRMP / GIS APIs</li>
        </ul>
      </div>
      <div className="text-xs text-brand-200">SIH 2026 · PS 26018 · Department of Land Resources, MoRD</div>
    </div>
    <div className="flex items-center justify-center p-6">
      <div className="w-full max-w-sm">
        <div className="lg:hidden mb-8"><Logo /></div>
        <h1 className="text-2xl font-semibold text-slate-900">Sign in</h1>
        <p className="text-sm text-slate-500 mt-1">Use your department account.</p>
        <form onSubmit={submit} className="mt-6 space-y-4">
          <div><label className="label" htmlFor="u">Username</label>
            <input id="u" className="input" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" autoFocus /></div>
          <div><label className="label" htmlFor="p">Password</label>
            <input id="p" type="password" className="input" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" /></div>
          <ErrorNote error={error} />
          <button className="btn-primary w-full" disabled={busy || !username || !password}><ShieldCheck size={16} /> {busy ? 'Signing in…' : 'Sign in'}</button>
        </form>
        <div className="mt-8 card p-3">
          <div className="label">Demo accounts</div>
          <div className="space-y-1">
            {DEMO.map(([u, p, d]) => (
              <button key={u} type="button" onClick={() => { setUsername(u); setPassword(p) }}
                className="w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-slate-50">
                <span className="font-medium text-slate-800">{u}</span> <span className="text-slate-400">/ {p}</span>
                <div className="text-xs text-slate-500">{d}</div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  </div>
}
