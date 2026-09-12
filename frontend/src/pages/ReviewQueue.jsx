import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ClipboardCheck, PartyPopper } from 'lucide-react'
import { api } from '../api'
import { ConfidenceBar, EmptyState, ErrorNote, fmtDate, PageHeader, SkeletonRows } from '../components/ui'
import { docTypeLabel } from '../constants'
import { useT } from '../i18n'
import { getQueueOrder, QUEUE_ORDER_KEY, sortQueue } from '../queue'

export default function ReviewQueue() {
  const { t, lang } = useT()
  const [rows, setRows] = useState(null)
  const [error, setError] = useState(null)
  // "confidence": the hardest documents first (default); "quick": fewest fields to check first,
  // for a verifier with a few minutes to spare. Remembered on this computer.
  const [order, setOrderState] = useState(getQueueOrder)
  const setOrder = (o) => { setOrderState(o); try { localStorage.setItem(QUEUE_ORDER_KEY, o) } catch { /* storage blocked */ } }
  useEffect(() => {
    const load = () => api.queue().then((v) => { setRows(v); setError(null) }).catch(setError)
    load()
    const t = setInterval(load, 5000)
    return () => clearInterval(t)
  }, [])

  const sorted = sortQueue(rows, order)

  return <div>
    <PageHeader title={t('Review queue')}
      subtitle={t(order === 'quick' ? 'Documents with at least one uncertain field — fewest fields to check first' : 'Documents with at least one uncertain field — lowest confidence first')}
      actions={sorted?.length > 0 && <Link to={`/documents/${sorted[0].id}`} className="btn-primary"><ClipboardCheck size={16} /> {t('Start reviewing')}</Link>} />
    <ErrorNote error={error} />
    <div className="card">
      {!rows ? <SkeletonRows cols={5} />
        : rows.length === 0 ? <EmptyState icon={PartyPopper} tone="ok" title={t('All clear')}
          action={<Link className="btn-outline" to="/documents">{t('Documents')}</Link>}>{t('Nothing waiting. Every processed document is either verified or passed automatically.')}</EmptyState>
          : <>
          <div className="flex flex-wrap gap-2 border-b border-slate-100 px-3 py-2.5" role="group" aria-label={t('Order')}>
            {[['confidence', 'Lowest confidence first'], ['quick', 'Fewest fields first']].map(([k, label]) =>
              <button key={k} onClick={() => setOrder(k)} aria-pressed={order === k}
                className={`min-h-8 rounded-full border px-3 text-xs font-medium transition-colors duration-200 ${order === k
                  ? 'border-brand-700 bg-brand-700 text-white' : 'border-slate-300 bg-white text-slate-700 hover:border-brand-500 hover:text-brand-700'}`}>{t(label)}</button>)}
          </div>
          {/* phones: one tappable card per document, in the chosen order */}
          <ul className="divide-y divide-slate-100 sm:hidden">{sorted.map((d) => <li key={d.id}>
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
            <tbody>{sorted.map((d) => <tr key={d.id}>
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
