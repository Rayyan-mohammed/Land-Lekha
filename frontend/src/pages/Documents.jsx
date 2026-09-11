import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { RefreshCw, Search } from 'lucide-react'
import { api } from '../api'
import { ConfidenceBar, Empty, ErrorNote, fmtDate, PageHeader, Spinner, StatusBadge } from '../components/ui'
import { STATUS } from '../constants'

export default function Documents() {
  const [params, setParams] = useSearchParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [q, setQ] = useState(params.get('q') || '')
  const status = params.get('status') || ''
  const page = Number(params.get('page') || 1)

  const load = () => api.documents({ status, q: params.get('q') || '', page, page_size: 20 }).then(setData).catch(setError)
  useEffect(() => { load() }, [params]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!data?.items.some((d) => d.status === 'queued' || d.status === 'processing')) return
    const t = setTimeout(load, 2000)
    return () => clearTimeout(t)
  }, [data]) // eslint-disable-line react-hooks/exhaustive-deps

  const set = (k, v) => { const p = new URLSearchParams(params); v ? p.set(k, v) : p.delete(k); if (k !== 'page') p.delete('page'); setParams(p) }
  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1

  return <div>
    <PageHeader title="Documents" subtitle={data ? `${data.total} document${data.total === 1 ? '' : 's'}` : ' '}
      actions={<button className="btn-outline" onClick={load}><RefreshCw size={15} /> Refresh</button>} />
    <div className="card">
      <div className="flex flex-wrap gap-2 border-b border-slate-100 p-3">
        <form onSubmit={(e) => { e.preventDefault(); set('q', q) }} className="relative flex-1 min-w-48">
          <Search size={15} className="absolute left-3 top-2.5 text-slate-400" />
          <input className="input pl-9" placeholder="Search file name or district" value={q} onChange={(e) => setQ(e.target.value)} />
        </form>
        <select className="input w-auto" value={status} onChange={(e) => set('status', e.target.value)}>
          <option value="">All statuses</option>
          {Object.entries(STATUS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
        </select>
      </div>
      <ErrorNote error={error} />
      {!data ? <div className="p-10 flex justify-center"><Spinner /></div>
        : data.items.length === 0 ? <Empty>No documents yet. <Link className="text-brand-700 underline" to="/upload">Upload one</Link>.</Empty>
          : <div className="table-wrap"><table className="data">
            <thead><tr><th>#</th><th>File</th><th>Type</th><th>District</th><th>Status</th><th>Confidence</th><th>Time</th><th>Uploaded</th></tr></thead>
            <tbody>{data.items.map((d) => <tr key={d.id}>
              <td className="text-slate-400 tabular-nums">{d.id}</td>
              <td><Link to={`/documents/${d.id}`} className="font-medium text-brand-700 hover:underline">{d.filename}</Link></td>
              <td className="text-slate-600">{d.document_type?.replaceAll('_', ' ') || '—'}</td>
              <td>{d.district || '—'}{d.state && <span className="text-slate-400"> · {d.state}</span>}</td>
              <td><StatusBadge status={d.status} /></td>
              <td><ConfidenceBar value={d.overall_confidence} /></td>
              <td className="tabular-nums text-slate-600">{d.processing_ms ? `${(d.processing_ms / 1000).toFixed(1)} s` : '—'}</td>
              <td className="text-slate-500 whitespace-nowrap">{fmtDate(d.created_at)}</td>
            </tr>)}</tbody>
          </table></div>}
      {pages > 1 && <div className="flex items-center justify-end gap-2 p-3 text-sm">
        <button className="btn-outline py-1" disabled={page <= 1} onClick={() => set('page', page - 1)}>Previous</button>
        <span className="text-slate-500">Page {page} of {pages}</span>
        <button className="btn-outline py-1" disabled={page >= pages} onClick={() => set('page', page + 1)}>Next</button>
      </div>}
    </div>
  </div>
}
