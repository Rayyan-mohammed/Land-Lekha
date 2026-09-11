import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { Empty, ErrorNote, fmtDate, PageHeader, SkeletonRows } from '../components/ui'

const ACTIONS = ['', 'auth', 'document', 'user', 'integration']

export default function Audit() {
  const [rows, setRows] = useState(null)
  const [total, setTotal] = useState(0)
  const [action, setAction] = useState('')
  const [page, setPage] = useState(1)
  const [error, setError] = useState(null)
  useEffect(() => {
    api.audit({ action, page, page_size: 50 }).then((r) => { setRows(r.items); setTotal(r.total) }).catch(setError)
  }, [action, page])

  return <div>
    <PageHeader title="Audit trail" subtitle={`${total} events · every upload, decision, correction, login and integration call`}
      actions={<select className="input w-auto" value={action} onChange={(e) => { setAction(e.target.value); setPage(1) }}>
        {ACTIONS.map((a) => <option key={a} value={a}>{a ? `${a}.*` : 'All actions'}</option>)}
      </select>} />
    <ErrorNote error={error} />
    <div className="card">
      {!rows ? <SkeletonRows cols={6} /> : rows.length === 0 ? <Empty>No events.</Empty> :
        <div className="table-wrap"><table className="data">
          <thead><tr><th>Time</th><th>User</th><th>Action</th><th>Entity</th><th>Details</th><th>IP</th></tr></thead>
          <tbody>{rows.map((r) => <tr key={r.id}>
            <td className="whitespace-nowrap text-slate-500">{fmtDate(r.ts)}</td>
            <td className="font-medium">{r.user}</td>
            <td><span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs">{r.action}</span></td>
            <td>{r.entity_type === 'document' ? <Link className="text-brand-700 hover:underline" to={`/documents/${r.entity_id}`}>document #{r.entity_id}</Link>
              : r.entity_type ? `${r.entity_type} #${r.entity_id ?? ''}` : '—'}</td>
            <td className="max-w-md truncate font-mono text-xs text-slate-600" title={JSON.stringify(r.details)}>{r.details ? JSON.stringify(r.details) : ''}</td>
            <td className="text-xs text-slate-500">{r.ip}</td>
          </tr>)}</tbody>
        </table></div>}
      {total > 50 && <div className="flex justify-end gap-2 p-3">
        <button className="btn-outline py-1" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
        <button className="btn-outline py-1" disabled={page * 50 >= total} onClick={() => setPage(page + 1)}>Next</button>
      </div>}
    </div>
  </div>
}
