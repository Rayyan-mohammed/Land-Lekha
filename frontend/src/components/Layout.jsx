import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { BarChart3, CircleHelp, ClipboardCheck, FileStack, LogOut, Map, Menu, ScrollText, Upload, Users, X } from 'lucide-react'
import { useAuth } from '../auth'
import { ROLE_LABEL } from '../constants'
import { LangToggle, useT } from '../i18n'
import { ErrorBoundary, OfflineBanner } from './Resilience'

const NAV = [
  { to: '/upload', label: 'Upload', icon: Upload, roles: ['operator', 'verifier'] },
  { to: '/documents', label: 'Documents', icon: FileStack, roles: ['operator', 'verifier'] },
  { to: '/review', label: 'Review queue', icon: ClipboardCheck, roles: ['verifier'] },
  { to: '/dashboard', label: 'Dashboard', icon: BarChart3, roles: ['verifier'] },
  { to: '/records', label: 'Records & GIS', icon: Map, roles: ['operator', 'verifier'] },
  { to: '/audit', label: 'Audit trail', icon: ScrollText, roles: [] },
  { to: '/users', label: 'Users', icon: Users, roles: [] },
  { to: '/help', label: 'Help', icon: CircleHelp, roles: ['operator', 'verifier'] },
]

export function Logo({ light = false }) {
  const { t } = useT()
  return <div className="flex items-center gap-2.5">
    <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden>
      <rect width="32" height="32" rx="7" fill={light ? '#fff' : '#0f3d3e'} />
      <path d="M8 22 L16 8 L24 22 Z" fill="none" stroke="#f2c14e" strokeWidth="2.5" />
      <path d="M11 22h10" stroke={light ? '#0f3d3e' : '#fff'} strokeWidth="2.5" />
    </svg>
    <div className="leading-tight">
      <div className={`font-semibold tracking-tight ${light ? 'text-white' : 'text-slate-900'}`}>LandLekha <span className="font-normal opacity-70">भूलेख</span></div>
      <div className={`text-[11px] ${light ? 'text-brand-100' : 'text-slate-500'}`}>{t('Land record digitization')}</div>
    </div>
  </div>
}

export default function Layout() {
  const { t } = useT()
  const location = useLocation()
  const { user, logout, can } = useAuth()
  const [open, setOpen] = useState(false)
  const items = NAV.filter((n) => can(...n.roles))

  const nav = <nav className="flex flex-col gap-1 p-3">
    {items.map(({ to, label, icon: Icon }) => (
      <NavLink key={to} to={to} onClick={() => setOpen(false)}
        className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${isActive ? 'bg-white/15 text-white' : 'text-brand-100 hover:bg-white/10 hover:text-white'}`}>
        <Icon size={17} /> {t(label)}
      </NavLink>
    ))}
  </nav>

  return <div className="min-h-full lg:flex">
    <a href="#main" className="skip-link btn-primary">Skip to content</a>
    <aside className={`fixed inset-y-0 left-0 z-40 w-60 transform bg-brand-800 transition lg:static lg:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'} flex flex-col`}>
      <div className="flex items-center justify-between px-4 py-4 border-b border-white/10">
        <Logo light />
        <button className="lg:hidden text-white" onClick={() => setOpen(false)} aria-label="close menu"><X size={20} /></button>
      </div>
      {nav}
      <div className="mt-auto border-t border-white/10 p-3">
        <div className="px-3 py-2">
          <div className="text-sm font-medium text-white truncate">{user?.full_name}</div>
          <div className="text-xs text-brand-100">{ROLE_LABEL[user?.role]} · {user?.username}</div>
        </div>
        <button onClick={logout} className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-brand-100 hover:bg-white/10 hover:text-white">
          <LogOut size={17} /> {t('Sign out')}
        </button>
        <LangToggle className="mx-3 mt-2 border-white/30 text-brand-100 hover:bg-white/10" />
      </div>
    </aside>
    {open && <div className="fixed inset-0 z-30 bg-black/30 lg:hidden" onClick={() => setOpen(false)} />}
    <div className="flex-1 min-w-0">
      <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur lg:hidden">
        <button onClick={() => setOpen(true)} aria-label="open menu"><Menu size={22} /></button>
        <Logo />
        <LangToggle className="ml-auto border-slate-300 text-slate-700" />
      </header>
      <OfflineBanner />
      <main id="main" tabIndex={-1} className="mx-auto max-w-7xl p-4 outline-none sm:p-6">
        {/* keyed by path: moving to another page clears a crash */}
        <ErrorBoundary key={location.pathname}><Outlet /></ErrorBoundary>
      </main>
    </div>
  </div>
}
