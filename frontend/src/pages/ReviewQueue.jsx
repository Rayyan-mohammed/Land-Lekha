import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ClipboardCheck, PartyPopper } from 'lucide-react'
import { api } from '../api'
import { ConfidenceBar, EmptyState, ErrorNote, fmtDate, PageHeader, SkeletonRows } from '../components/ui'
import { docTypeLabel } from '../constants'
import { useT } from '../i18n'

export default function ReviewQueue() {
  const { t, lang } = useT()
  const [rows, setRows] = useState(null)
  const [error, setError] = useState(null)
  useEffect(() => {
    const load = () => api.queue().then(setRows).catch(setError)
    load()
    const t = setInterval(load, 5000)
    return () => clearInterval(t)
  }, [])

  return <div>
    <PageHeader title={t('Review queue')} subtitle={t('Documents with at least one uncertain field — lowest confidence first')}
      actions={rows?.length > 0 && <Link to={`/documents/${rows[0].id}`} className="btn-primary"><ClipboardCheck size={16} /> {t('Start reviewing')}</Link>} />
    <ErrorNote error={error} />
    <div className="card">
      {!rows ? <SkeletonRows cols={5} />
        : rows.length === 0 ? <EmptyState icon={PartyPopper} tone="ok" title={t('All clear')}
          action={<Link className="btn-outline" to="/documents">{t('Documents')}</Link>}>{t('Nothing waiting. Every processed document is either verified or passed automatically.')}</EmptyState>
          : <>
          {/* phones: one tappable card per document, lowest confidence first */}
          <ul className="divide-y divide-slate-100 sm:hidden">{rows.map((d) => <li key={d.id}>
            <Link to={`/documents/${d.id}`} className="flex items-center gap-3 px-4 py-3 transition-colors duration-200 active:bg-slate-50">
              <div className="min-w-0 flex-1">
                <div className="truncate font-medium text-slate-900">{d.filename}</div>
                <div className="mt-0.5 text-xs text-slate-500">#{d.id} · {d.document_type ? docTypeLabel(d.document_type, lang) : '—'} · {d.district || '—'} · {fmtDate(d.created_at)}</div>
                <div className="mt-1.5 flex items-center gap-3"><ConfidenceBar value={d.overall_confidence} />
                  {d.flagged > 0 && <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-warn">{d.flagged} {t('to check')}</span>}</div>
              </div>
              <span className="text-sm font-medium text-brand-700">{t('Review')} →</span>
            </Link></li>)}</ul>
          <div className="table-wrap hidden sm:block"><table className="data">
            <thead><tr><th>#</th><th>{t('File')}</th><th>{t('District')}</th><th>{t('Confidence')}</th><th>{t('To check')}</th><th>{t('Uploaded')}</th><th><span className="sr-only">{t('Actions')}</span></th></tr></thead>
            <tbody>{rows.map((d) => <tr key={d.id}>
              <td className="text-slate-500 tabular-nums">{d.id}</td>
              <td className="font-medium">{d.filename}<div className="text-xs font-normal text-slate-500">{d.document_type && docTypeLabel(d.document_type, lang)}</div></td>
              <td>{d.district || '—'}</td>
              <td><ConfidenceBar value={d.overall_confidence} /></td>
              <td className="tabular-nums">{d.flagged > 0 ? <span className="font-medium text-warn">{d.flagged}</span> : (d.flagged ?? '—')}</td>
              <td className="text-slate-500 whitespace-nowrap">{fmtDate(d.created_at)}</td>
              <td className="text-right"><Link to={`/documents/${d.id}`} className="btn-outline py-1">{t('Review')}</Link></td>
            </tr>)}</tbody>
          </table></div></>}
    </div>
  </div>
}
