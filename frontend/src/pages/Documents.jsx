import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { FileUp, RefreshCw, Search } from 'lucide-react'
import { api } from '../api'
import { ConfidenceBar, EmptyState, ErrorNote, fmtDate, PageHeader, SkeletonRows, StatusBadge } from '../components/ui'
import { docTypeLabel, STATUS } from '../constants'
import { useT } from '../i18n'

export default function Documents() {
  const { t, lang } = useT()
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
    <PageHeader title={t('Documents')} subtitle={data ? `${data.total} ${t(data.total === 1 ? 'document' : 'documents')}` : ' '}
      actions={<button className="btn-outline" onClick={load}><RefreshCw size={15} /> {t('Refresh')}</button>} />
    <div className="card">
      <div className="flex flex-wrap gap-2 border-b border-slate-100 p-3">
        <form onSubmit={(e) => { e.preventDefault(); set('q', q) }} className="relative flex-1 min-w-48">
          <Search size={15} className="absolute left-3 top-2.5 text-slate-500" />
          <input className="input pl-9" placeholder={t('Search file name or district')} value={q} onChange={(e) => setQ(e.target.value)} />
        </form>
      </div>
      {data?.counts && <div className="flex flex-wrap gap-2 border-b border-slate-100 px-3 py-2.5" role="group" aria-label={t('Status')}>
        {[['', t('All statuses'), Object.values(data.counts).reduce((x, y) => x + y, 0)],
          ...Object.keys(STATUS).filter((k) => data.counts[k]).map((k) => [k, t(STATUS[k].label), data.counts[k]])].map(([k, label, n]) =>
          <button key={k || 'all'} onClick={() => set('status', k)} aria-pressed={status === k}
            className={`inline-flex min-h-8 items-center gap-1.5 rounded-full border px-3 text-xs font-medium transition-colors duration-200 ${status === k
              ? 'border-brand-700 bg-brand-700 text-white' : 'border-slate-300 bg-white text-slate-700 hover:border-brand-500 hover:text-brand-700'}`}>
            {label}<span className={`rounded-full px-1.5 tabular-nums ${status === k ? 'bg-white/20' : 'bg-slate-100 text-slate-600'}`}>{n}</span>
          </button>)}
      </div>}
      <ErrorNote error={error} />
      {!data ? <SkeletonRows cols={6} />
        : data.items.length === 0 ? <EmptyState icon={FileUp} title={t(status || params.get('q') ? 'Nothing matches this filter' : 'No documents yet')}
          action={!status && !params.get('q') && <Link className="btn-primary" to="/upload"><FileUp size={16} /> {t('Upload land records')}</Link>}>
          {t(status || params.get('q') ? 'Try another status or search term.' : 'Scanned records you upload will appear here with their status and confidence.')}</EmptyState>
          : <>
          {/* phones: one tappable card per document instead of a wide table */}
          <ul className="divide-y divide-slate-100 sm:hidden">{data.items.map((d) => <li key={d.id}>
            <Link to={`/documents/${d.id}`} className="flex items-start gap-3 px-4 py-3 transition-colors duration-200 active:bg-slate-50">
              <div className="min-w-0 flex-1">
                <div className="truncate font-medium text-brand-700">{d.filename}</div>
                <div className="mt-0.5 text-xs text-slate-500">#{d.id} · {d.document_type ? docTypeLabel(d.document_type, lang) : '—'} · {d.district || '—'}</div>
                <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1"><ConfidenceBar value={d.overall_confidence} /><span className="text-xs text-slate-500">{fmtDate(d.created_at)}</span>
                  {d.status === 'needs_review' && d.flagged > 0 && <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-warn">{d.flagged} {t('to check')}</span>}</div>
              </div>
              <StatusBadge status={d.status} />
            </Link></li>)}</ul>
          <div className="table-wrap hidden sm:block"><table className="data">
            <thead><tr><th>#</th><th>{t('File')}</th><th>{t('Type')}</th><th>{t('District')}</th><th>{t('Status')}</th><th>{t('Confidence')}</th><th>{t('Time')}</th><th>{t('Uploaded')}</th></tr></thead>
            <tbody>{data.items.map((d) => <tr key={d.id}>
              <td className="text-slate-500 tabular-nums">{d.id}</td>
              <td><Link to={`/documents/${d.id}`} className="font-medium text-brand-700 hover:underline">{d.filename}</Link></td>
              <td className="text-slate-600">{d.document_type ? docTypeLabel(d.document_type, lang) : '—'}</td>
              <td>{d.district || '—'}{d.state && <span className="text-slate-500"> · {d.state}</span>}</td>
              <td><StatusBadge status={d.status} />
                {d.status === 'needs_review' && d.flagged > 0 && <div className="mt-0.5 text-xs text-warn">{d.flagged} {t('to check')}</div>}</td>
              <td><ConfidenceBar value={d.overall_confidence} /></td>
              <td className="tabular-nums text-slate-600">{d.processing_ms ? `${(d.processing_ms / 1000).toFixed(1)} s` : '—'}</td>
              <td className="text-slate-500 whitespace-nowrap">{fmtDate(d.created_at)}</td>
            </tr>)}</tbody>
          </table></div></>}
      {pages > 1 && <div className="flex items-center justify-end gap-2 p-3 text-sm">
        <button className="btn-outline py-1" disabled={page <= 1} onClick={() => set('page', page - 1)}>{t('Previous')}</button>
        <span className="text-slate-500">{t('Page')} {page} / {pages}</span>
        <button className="btn-outline py-1" disabled={page >= pages} onClick={() => set('page', page + 1)}>{t('Next')}</button>
      </div>}
    </div>
  </div>
}
