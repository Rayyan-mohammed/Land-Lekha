import { useEffect, useState } from 'react'
import { ClipboardCheck, Copy, KeyRound, ShieldCheck, Upload, UserPlus, X } from 'lucide-react'
import { api } from '../api'
import { useAuth } from '../auth'
import { ErrorNote, PageHeader, SkeletonRows } from '../components/ui'
import { ROLE_LABEL } from '../constants'
import { useToast } from '../components/toast'
import { useT } from '../i18n'

const ROLE_INFO = {
  operator: [Upload, 'bg-sky-50 text-sky-800', 'Uploads records and sees their own uploads'],
  verifier: [ClipboardCheck, 'bg-amber-50 text-amber-800', 'Reviews flagged fields, approves records, issues extracts'],
  admin: [ShieldCheck, 'bg-brand-50 text-brand-800', 'Everything, plus users, the full audit trail and re-processing'],
}

// strong, readable temporary password (no look-alike characters)
function tempPassword() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789'
  const bytes = crypto.getRandomValues(new Uint8Array(12))
  return Array.from(bytes, (b) => chars[b % chars.length]).join('').replace(/(.{4})(?=.)/g, '$1-')
}

// two-letter avatar from a full name, ignoring brackets and punctuation ("Verifier (Tehsil)" -> "VT")
const initials = (name) => name.split(' ').map((w) => w.replace(/[^\p{L}]/gu, '')[0]).filter(Boolean).slice(0, 2).join('').toUpperCase()

export default function UsersPage() {
  const { user: me } = useAuth()
  const { t } = useT()
  const toast = useToast()
  const [users, setUsers] = useState(null)
  const [form, setForm] = useState({ username: '', full_name: '', role: 'operator', password: '' })
  const [error, setError] = useState(null)
  const [reset, setReset] = useState(null) // {user, password}
  const load = () => api.users().then(setUsers).catch(setError)
  useEffect(() => { load() }, [])

  const create = async (e) => {
    e.preventDefault()
    setError(null)
    try {
      await api.createUser(form)
      toast(`${t('Account created for')} ${form.full_name}`, { body: `${form.username} · ${t(ROLE_LABEL[form.role])}` })
      setForm({ username: '', full_name: '', role: 'operator', password: '' }); load()
    } catch (err) { setError(err) }
  }
  const update = (u, body) => api.updateUser(u.id, body).then(() => {
    toast(`${u.full_name} ${t('updated')}`, { body: body.active === false ? t('Account disabled') : body.active ? t('Account enabled') : `${t('Role')}: ${t(ROLE_LABEL[body.role] || '')}` })
    load()
  }).catch(setError)
  const resetPassword = async (u) => {
    const password = tempPassword()
    try {
      await api.updateUser(u.id, { password })
      setReset({ user: u, password })
    } catch (err) { setError(err) }
  }

  return <div>
    <PageHeader title={t('Users & roles')} subtitle={t('Who can do what in LandLekha. Every change here is recorded in the audit trail.')} />
    <ErrorNote error={error} />
    <div className="mb-4 grid gap-3 sm:grid-cols-3">
      {Object.entries(ROLE_INFO).map(([role, [Icon, cls, text]]) => <div key={role} className="card flex items-start gap-3 p-3">
        <div className={`rounded-lg p-2 ${cls}`}><Icon size={16} /></div>
        <div><div className="text-sm font-medium text-slate-900">{t(ROLE_LABEL[role])}</div><div className="text-xs text-slate-600">{t(text)}</div></div>
      </div>)}
    </div>

    {reset && <div role="dialog" aria-label="temporary password" className="animate-rise mb-4 flex flex-wrap items-center gap-3 rounded-xl border border-brand-200 bg-brand-50 p-4">
      <KeyRound size={18} className="text-brand-700" />
      <div className="min-w-0 flex-1 text-sm">
        <div className="font-medium text-slate-900">{t('New temporary password for')} {reset.user.full_name}</div>
        <div className="text-xs text-slate-600">{t('Shown only once. Give it to them in person; they should change it after signing in.')}</div>
      </div>
      <code className="rounded-lg bg-white px-3 py-1.5 font-mono text-base tracking-wider text-slate-900 ring-1 ring-slate-200">{reset.password}</code>
      <button className="btn-outline" onClick={() => { navigator.clipboard?.writeText(reset.password); toast(t('Password copied')) }}><Copy size={15} /> {t('Copy')}</button>
      <button className="btn-ghost px-2" aria-label={t('Close')} onClick={() => setReset(null)}><X size={16} /></button>
    </div>}

    <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
      <div className="card">
        {!users ? <SkeletonRows cols={4} rows={4} /> : <>
          {/* phones: one card per account, so status and actions are not off-screen */}
          <ul className="divide-y divide-slate-100 sm:hidden">{users.map((u) => {
            const [Icon, cls] = ROLE_INFO[u.role] || ROLE_INFO.operator
            return <li key={u.id} className={`space-y-2 px-4 py-3 ${u.active ? '' : 'opacity-60'}`}>
              <div className="flex items-center gap-2.5">
                <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${cls}`} aria-hidden>{initials(u.full_name)}</div>
                <div className="min-w-0 flex-1">
                  <div className="truncate font-medium">{u.full_name}{u.id === me.id && <span className="ml-1.5 text-xs font-normal text-slate-500">({t('you')})</span>}</div>
                  <div className="text-xs text-slate-500">{u.username}</div>
                </div>
                {u.active ? <span className="inline-flex items-center gap-1 text-xs text-ok"><span className="h-2 w-2 rounded-full bg-ok" /> {t('Active')}</span>
                  : <span className="text-xs text-slate-500">{t('Disabled')}</span>}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Icon size={14} className="text-slate-500" />
                <select aria-label={`${t('Role')}: ${u.full_name}`} className="input w-auto py-1" value={u.role} disabled={u.id === me.id} onChange={(e) => update(u, { role: e.target.value })}>
                  {Object.entries(ROLE_LABEL).map(([k, v]) => <option key={k} value={k}>{t(v)}</option>)}</select>
                {u.id !== me.id && <>
                  <button className="btn-ghost py-1 text-xs" onClick={() => resetPassword(u)}><KeyRound size={13} /> {t('Reset password')}</button>
                  <button className="btn-ghost py-1 text-xs" onClick={() => update(u, { active: !u.active })}>{t(u.active ? 'Disable' : 'Enable')}</button>
                </>}
              </div>
            </li>
          })}</ul>
          <div className="table-wrap hidden sm:block"><table className="data">
            <thead><tr><th>{t('User')}</th><th>{t('Role')}</th><th>{t('Status')}</th><th /></tr></thead>
            <tbody>{users.map((u) => {
              const [Icon, cls] = ROLE_INFO[u.role] || ROLE_INFO.operator
              return <tr key={u.id} className={u.active ? '' : 'opacity-60'}>
                <td><div className="flex items-center gap-2.5">
                  <div className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold ${cls}`} aria-hidden>
                    {initials(u.full_name)}</div>
                  <div><div className="font-medium">{u.full_name}{u.id === me.id && <span className="ml-1.5 text-xs font-normal text-slate-500">({t('you')})</span>}</div>
                    <div className="text-xs text-slate-500">{u.username}</div></div></div></td>
                <td><div className="flex items-center gap-1.5"><Icon size={14} className="text-slate-500" />
                  <select aria-label={`${t('Role')}: ${u.full_name}`} className="input w-auto py-1" value={u.role} disabled={u.id === me.id} onChange={(e) => update(u, { role: e.target.value })}>
                    {Object.entries(ROLE_LABEL).map(([k, v]) => <option key={k} value={k}>{t(v)}</option>)}</select></div></td>
                <td>{u.active ? <span className="inline-flex items-center gap-1 text-sm text-ok"><span className="h-2 w-2 rounded-full bg-ok" /> {t('Active')}</span>
                  : <span className="text-sm text-slate-500">{t('Disabled')}</span>}</td>
                <td className="whitespace-nowrap text-right">{u.id !== me.id && <>
                  <button className="btn-ghost py-1 text-xs" onClick={() => resetPassword(u)}><KeyRound size={13} /> {t('Reset password')}</button>
                  <button className="btn-ghost py-1 text-xs" onClick={() => update(u, { active: !u.active })}>{t(u.active ? 'Disable' : 'Enable')}</button>
                </>}</td>
              </tr>
            })}</tbody>
          </table></div></>}
      </div>
      <form onSubmit={create} className="card h-fit space-y-3 p-4">
        <div className="flex items-center gap-2 font-medium"><UserPlus size={16} /> {t('Add user')}</div>
        <div><label className="label" htmlFor="nu-username">{t('Username')}</label><input id="nu-username" className="input" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /></div>
        <div><label className="label" htmlFor="nu-name">{t('Full name')}</label><input id="nu-name" className="input" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></div>
        <div><label className="label" htmlFor="nu-role">{t('Role')}</label><select id="nu-role" className="input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
          {Object.entries(ROLE_LABEL).map(([k, v]) => <option key={k} value={k}>{t(v)}</option>)}</select></div>
        <div><label className="label" htmlFor="nu-pw">{t('Password (min 8)')}</label>
          <div className="flex gap-2"><input id="nu-pw" type="text" autoComplete="new-password" className="input font-mono" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
            <button type="button" className="btn-outline shrink-0" onClick={() => setForm({ ...form, password: tempPassword() })}>{t('Generate')}</button></div></div>
        <button className="btn-primary w-full" disabled={!form.username || !form.full_name || form.password.length < 8}>{t('Create user')}</button>
      </form>
    </div>
  </div>
}
