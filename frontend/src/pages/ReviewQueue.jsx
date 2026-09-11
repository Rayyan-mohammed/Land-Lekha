import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ClipboardCheck } from 'lucide-react'
import { api } from '../api'
import { ConfidenceBar, Empty, ErrorNote, fmtDate, PageHeader, Spinner } from '../components/ui'
import { useT } from '../i18n'

export default function ReviewQueue() {
  const { t } = useT()
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
      {!rows ? <div className="p-10 flex justify-center"><Spinner /></div>
        : rows.length === 0 ? <Empty>{t('Nothing waiting. Every processed document is either verified or passed automatically.')}</Empty>
          : <div className="table-wrap"><table className="data">
            <thead><tr><th>#</th><th>{t('File')}</th><th>{t('District')}</th><th>{t('Confidence')}</th><th>{t('Uploaded')}</th><th /></tr></thead>
            <tbody>{rows.map((d) => <tr key={d.id}>
              <td className="text-slate-400 tabular-nums">{d.id}</td>
              <td className="font-medium">{d.filename}<div className="text-xs font-normal text-slate-500">{d.document_type?.replaceAll('_', ' ')}</div></td>
              <td>{d.district || '—'}</td>
              <td><ConfidenceBar value={d.overall_confidence} /></td>
              <td className="text-slate-500 whitespace-nowrap">{fmtDate(d.created_at)}</td>
              <td className="text-right"><Link to={`/documents/${d.id}`} className="btn-outline py-1">{t('Review')}</Link></td>
            </tr>)}</tbody>
          </table></div>}
    </div>
  </div>
}
