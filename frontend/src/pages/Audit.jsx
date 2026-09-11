import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CheckCircle2, FileText, FileUp, KeyRound, LogIn, Printer, RotateCcw, Send, ShieldAlert, UserCog, XCircle } from 'lucide-react'
import { api } from '../api'
import { EmptyState, ErrorNote, fmtDate, PageHeader, parseTs, SkeletonRows } from '../components/ui'

const FILTERS = [['', 'Everything'], ['document', 'Documents'], ['record', 'Extracts'], ['integration', 'LRMS / GIS'], ['user', 'Users'], ['auth', 'Sign-ins']]

// plain-language description, icon and tone for each kind of audit event
const EVENTS = {
  'auth.login': [LogIn, 'slate', () => 'signed in'],
  'auth.login_failed': [ShieldAlert, 'bad', (d) => `failed sign-in attempt${d?.username ? ` for "${d.username}"` : ''}`],
  'document.uploaded': [FileUp, 'brand', (d) => `uploaded ${d?.filename || 'a file'}`],
  'document.duplicate_upload': [FileText, 'slate', (d) => `tried to upload ${d?.filename || 'a file'} again (already on record)`],
  'document.processed': [FileText, 'brand', (d) => d?.route === 'auto_accept'
    ? `read and accepted automatically (${Math.round((d.confidence || 0) * 100)}% confidence)`
    : `read; sent to a verifier (${Math.round((d?.confidence || 0) * 100)}% confidence)`],
  'document.failed': [XCircle, 'bad', (d) => `could not be processed${d?.error ? `: ${d.error.slice(0, 80)}` : ''}`],
  'document.verified': [CheckCircle2, 'ok', (d) => `approved the record${d?.changes?.length ? ` with ${d.changes.length} correction${d.changes.length > 1 ? 's' : ''}` : ''}`],
  'document.rejected': [XCircle, 'bad', (d) => `rejected the document${d?.note ? `: "${d.note}"` : ''}`],
  'document.reprocess': [RotateCcw, 'slate', () => 'ran processing again'],
  'record.extract_issued': [Printer, 'brand', (d) => `issued a verified extract (fingerprint ${d?.fingerprint || ''})`],
  'integration.lrms_push': [Send, 'ok', (d) => `sent the record to LRMS (${d?.lrms_ref || ''})`],
  'user.created': [UserCog, 'brand', (d) => `created the account ${d?.username || ''} (${d?.role || ''})`],
  'user.updated': [KeyRound, 'slate', (d) => `changed an account: ${Object.keys(d || {}).join(', ')}`],
}
const TONES = { brand: 'bg-brand-50 text-brand-700', ok: 'bg-emerald-50 text-ok', bad: 'bg-red-50 text-bad', slate: 'bg-slate-100 text-slate-600' }

function ago(ts) {
  const s = (Date.now() - parseTs(ts).getTime()) / 1000
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)} min ago`
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`
  return fmtDate(ts)
}

function Subject({ r }) {
  if (r.entity_type === 'document') return <Link className="font-medium text-brand-700 hover:underline" to={`/documents/${r.entity_id}`}>document #{r.entity_id}</Link>
  if (r.entity_type === 'land_record') return <Link className="font-medium text-brand-700 hover:underline" to={`/records?focus=${r.entity_id}`}>record #{r.entity_id}</Link>
  if (r.entity_type === 'user' && r.entity_id) return <span className="font-medium">user #{r.entity_id}</span>
  return null
}

export default function Audit() {
  const [rows, setRows] = useState(null)
  const [total, setTotal] = useState(0)
  const [action, setAction] = useState('')
  const [page, setPage] = useState(1)
  const [error, setError] = useState(null)
  useEffect(() => {
    setRows(null)
    api.audit({ action, page, page_size: 50 }).then((r) => { setRows(r.items); setTotal(r.total) }).catch(setError)
  }, [action, page])

  return <div>
    <PageHeader title="Audit trail" subtitle={`${total} events · every upload, decision, correction, sign-in and integration call, with who and when`} />
    <div className="mb-3 flex flex-wrap gap-2" role="group" aria-label="filter events">
      {FILTERS.map(([k, label]) => <button key={k || 'all'} aria-pressed={action === k} onClick={() => { setAction(k); setPage(1) }}
        className={`min-h-8 rounded-full border px-3 text-xs font-medium transition-colors duration-200 ${action === k
          ? 'border-brand-700 bg-brand-700 text-white' : 'border-slate-300 bg-white text-slate-700 hover:border-brand-500 hover:text-brand-700'}`}>{label}</button>)}
    </div>
    <ErrorNote error={error} />
    <div className="card">
      {!rows ? <SkeletonRows cols={4} /> : rows.length === 0 ? <EmptyState icon={FileText} title="No events here yet" /> :
        <ol className="divide-y divide-slate-100">
          {rows.map((r) => {
            const [Icon, tone, describe] = EVENTS[r.action] || [FileText, 'slate', () => r.action]
            return <li key={r.id} className="flex items-start gap-3 px-4 py-3">
              <div className={`mt-0.5 rounded-lg p-1.5 ${TONES[tone]}`}><Icon size={15} /></div>
              <div className="min-w-0 flex-1 text-sm">
                <div className="text-slate-800"><span className="font-medium">{r.user || 'system'}</span> {describe(r.details)}
                  {r.entity_type && !r.action.startsWith('auth.') && <> · <Subject r={r} /></>}</div>
                {r.details?.changes?.length > 0 && <div className="mt-0.5 text-xs text-slate-600">
                  {r.details.changes.map((c) => c.rejected ? `${c.field} rejected` : `${c.field}: ${c.from ?? '—'} → ${c.to}`).join(' · ')}</div>}
                <div className="mt-0.5 text-xs text-slate-500">
                  <time dateTime={r.ts} title={parseTs(r.ts).toLocaleString()}>{ago(r.ts)}</time>{r.ip && ` · ${r.ip}`}
                  <span className="ml-2 font-mono text-[10px] text-slate-500">{r.action}</span></div>
              </div>
            </li>
          })}
        </ol>}
      {total > 50 && <div className="flex items-center justify-end gap-2 border-t border-slate-100 p-3 text-sm">
        <button className="btn-outline py-1" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
        <span className="text-slate-500">Page {page} of {Math.ceil(total / 50)}</span>
        <button className="btn-outline py-1" disabled={page * 50 >= total} onClick={() => setPage(page + 1)}>Next</button>
      </div>}
    </div>
  </div>
}
