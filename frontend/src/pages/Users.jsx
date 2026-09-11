import { useEffect, useState } from 'react'
import { UserPlus } from 'lucide-react'
import { api } from '../api'
import { useAuth } from '../auth'
import { ErrorNote, PageHeader, SkeletonRows } from '../components/ui'
import { ROLE_LABEL } from '../constants'
import { useToast } from '../components/toast'

export default function UsersPage() {
  const { user: me } = useAuth()
  const toast = useToast()
  const [users, setUsers] = useState(null)
  const [form, setForm] = useState({ username: '', full_name: '', role: 'operator', password: '' })
  const [error, setError] = useState(null)
  const load = () => api.users().then(setUsers).catch(setError)
  useEffect(() => { load() }, [])

  const create = async (e) => {
    e.preventDefault()
    setError(null)
    try {
      await api.createUser(form)
      toast(`Account created for ${form.full_name}`, { body: `${form.username} · ${ROLE_LABEL[form.role]}` })
      setForm({ username: '', full_name: '', role: 'operator', password: '' }); load()
    } catch (err) { setError(err) }
  }
  const update = (u, body) => api.updateUser(u.id, body).then(() => {
    toast(`${u.full_name} updated`, { body: body.active === false ? 'Account disabled' : body.active ? 'Account enabled' : `Role: ${ROLE_LABEL[body.role] || ''}` })
    load()
  }).catch(setError)

  return <div>
    <PageHeader title="Users & roles" subtitle="Operators upload · verifiers review and approve · administrators manage everything" />
    <ErrorNote error={error} />
    <div className="grid gap-4 lg:grid-cols-[1fr_320px] mt-3">
      <div className="card">
        {!users ? <SkeletonRows cols={4} rows={4} /> :
          <div className="table-wrap"><table className="data">
            <thead><tr><th>User</th><th>Role</th><th>Status</th><th /></tr></thead>
            <tbody>{users.map((u) => <tr key={u.id}>
              <td><div className="font-medium">{u.full_name}</div><div className="text-xs text-slate-500">{u.username}</div></td>
              <td><select aria-label={`Role of ${u.full_name}`} className="input w-auto py-1" value={u.role} disabled={u.id === me.id} onChange={(e) => update(u, { role: e.target.value })}>
                {Object.entries(ROLE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></td>
              <td>{u.active ? <span className="text-ok text-sm">Active</span> : <span className="text-slate-500 text-sm">Disabled</span>}</td>
              <td className="text-right">{u.id !== me.id && <button className="btn-ghost py-1 text-xs" onClick={() => update(u, { active: !u.active })}>{u.active ? 'Disable' : 'Enable'}</button>}</td>
            </tr>)}</tbody>
          </table></div>}
      </div>
      <form onSubmit={create} className="card p-4 space-y-3 h-fit">
        <div className="font-medium flex items-center gap-2"><UserPlus size={16} /> Add user</div>
        <div><label className="label" htmlFor="nu-username">Username</label><input id="nu-username" className="input" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /></div>
        <div><label className="label" htmlFor="nu-name">Full name</label><input id="nu-name" className="input" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></div>
        <div><label className="label" htmlFor="nu-role">Role</label><select id="nu-role" className="input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
          {Object.entries(ROLE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div>
        <div><label className="label" htmlFor="nu-pw">Password (min 8)</label><input id="nu-pw" type="password" autoComplete="new-password" className="input" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></div>
        <button className="btn-primary w-full" disabled={!form.username || !form.full_name || form.password.length < 8}>Create user</button>
      </form>
    </div>
  </div>
}
