import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CheckCircle2, FileText, FileUp, KeyRound, LogIn, Printer, RotateCcw, Send, ShieldAlert, UserCog, XCircle } from 'lucide-react'
import { api } from '../api'
import { EmptyState, ErrorNote, fmtDate, locale, PageHeader, parseTs, SkeletonRows } from '../components/ui'
import { FIELD_MAP } from '../constants'
import { useT } from '../i18n'

const FILTERS = [['', 'Everything'], ['document', 'Documents'], ['record', 'Extracts'], ['integration', 'LRMS / GIS'], ['user', 'Users'], ['auth', 'Sign-ins']]

const pct = (d) => Math.round((d?.confidence || 0) * 100)

// plain-language description [English, Hindi], icon and tone for each kind of audit event.
// The Hindi follows the actor's name, so it is written for "<name> ने ..." word order.
const EVENTS = {
  'auth.login': [LogIn, 'slate', () => ['signed in', 'ने साइन इन किया']],
  'auth.login_failed': [ShieldAlert, 'bad', (d) => [`failed sign-in attempt${d?.username ? ` for "${d.username}"` : ''}`,
    `— साइन इन का असफल प्रयास${d?.username ? ` ("${d.username}")` : ''}`]],
  'document.uploaded': [FileUp, 'brand', (d) => [`uploaded ${d?.filename || 'a file'}`, `ने ${d?.filename || 'एक फ़ाइल'} अपलोड की`]],
  'document.duplicate_upload': [FileText, 'slate', (d) => [`tried to upload ${d?.filename || 'a file'} again (already on record)`,
    `ने ${d?.filename || 'एक फ़ाइल'} दोबारा अपलोड करनी चाही (पहले से मौजूद)`]],
  'document.processed': [FileText, 'brand', (d) => (d?.route === 'auto_accept'
    ? [`read and accepted automatically (${pct(d)}% confidence)`, `ने पढ़ा और अपने आप स्वीकृत किया (${pct(d)}% विश्वसनीयता)`]
    : [`read; sent to a verifier (${pct(d)}% confidence)`, `ने पढ़ा और जाँचकर्ता को भेजा (${pct(d)}% विश्वसनीयता)`])],
  'document.failed': [XCircle, 'bad', (d) => [`could not be processed${d?.error ? `: ${d.error.slice(0, 80)}` : ''}`,
    `इसे संसाधित नहीं कर सका${d?.error ? `: ${d.error.slice(0, 80)}` : ''}`]],
  'document.verified': [CheckCircle2, 'ok', (d) => {
    const n = d?.changes?.length || 0
    return [`approved the record${n ? ` with ${n} correction${n > 1 ? 's' : ''}` : ''}`, `ने अभिलेख स्वीकृत किया${n ? ` (${n} सुधार)` : ''}`]
  }],
  'document.rejected': [XCircle, 'bad', (d) => [`rejected the document${d?.note ? `: "${d.note}"` : ''}`,
    `ने दस्तावेज़ अस्वीकार किया${d?.note ? `: "${d.note}"` : ''}`]],
  'document.reprocess': [RotateCcw, 'slate', () => ['ran processing again', 'ने दोबारा संसाधन चलाया']],
  'record.extract_issued': [Printer, 'brand', (d) => [`issued a verified extract (fingerprint ${d?.fingerprint || ''})`,
    `ने सत्यापित नकल जारी की (फ़िंगरप्रिंट ${d?.fingerprint || ''})`]],
  'integration.lrms_push': [Send, 'ok', (d) => [`sent the record to LRMS (${d?.lrms_ref || ''})`, `ने अभिलेख LRMS को भेजा (${d?.lrms_ref || ''})`]],
  'user.created': [UserCog, 'brand', (d) => [`created the account ${d?.username || ''} (${d?.role || ''})`,
    `ने खाता ${d?.username || ''} बनाया (${d?.role || ''})`]],
  'user.updated': [KeyRound, 'slate', (d) => [`changed an account: ${Object.keys(d || {}).join(', ')}`, `ने खाता बदला: ${Object.keys(d || {}).join(', ')}`]],
}
const TONES = { brand: 'bg-brand-50 text-brand-700', ok: 'bg-emerald-50 text-ok', bad: 'bg-red-50 text-bad', slate: 'bg-slate-100 text-slate-600' }

function ago(ts, hi) {
  const s = (Date.now() - parseTs(ts).getTime()) / 1000
  if (s < 60) return hi ? 'अभी' : 'just now'
  if (s < 3600) return hi ? `${Math.floor(s / 60)} मिनट पहले` : `${Math.floor(s / 60)} min ago`
  if (s < 86400) return hi ? `${Math.floor(s / 3600)} घंटे पहले` : `${Math.floor(s / 3600)} h ago`
  return fmtDate(ts)
}

function Subject({ r, hi }) {
  if (r.entity_type === 'document') return <Link className="font-medium text-brand-700 hover:underline" to={`/documents/${r.entity_id}`}>{hi ? 'दस्तावेज़' : 'document'} #{r.entity_id}</Link>
  if (r.entity_type === 'land_record') return <Link className="font-medium text-brand-700 hover:underline" to={`/records?focus=${r.entity_id}`}>{hi ? 'अभिलेख' : 'record'} #{r.entity_id}</Link>
  if (r.entity_type === 'user' && r.entity_id) return <span className="font-medium">{hi ? 'उपयोगकर्ता' : 'user'} #{r.entity_id}</span>
  return null
}

export default function Audit() {
  const { t, lang } = useT()
  const hi = lang === 'hi'
  const [rows, setRows] = useState(null)
  const [total, setTotal] = useState(0)
  const [action, setAction] = useState('')
  const [page, setPage] = useState(1)
  const [error, setError] = useState(null)
  useEffect(() => {
    setRows(null)
    api.audit({ action, page, page_size: 50 }).then((r) => { setRows(r.items); setTotal(r.total) }).catch(setError)
  }, [action, page])
  const fieldName = (n) => FIELD_MAP[n]?.[hi ? 'hi' : 'en'] || n

  return <div>
    <PageHeader title={t('Audit trail')} subtitle={`${total} ${t('events')} · ${t('every upload, decision, correction, sign-in and integration call, with who and when')}`} />
    <div className="mb-3 flex flex-wrap gap-2" role="group" aria-label={t('filter events')}>
      {FILTERS.map(([k, label]) => <button key={k || 'all'} aria-pressed={action === k} onClick={() => { setAction(k); setPage(1) }}
        className={`min-h-8 rounded-full border px-3 text-xs font-medium transition-colors duration-200 ${action === k
          ? 'border-brand-700 bg-brand-700 text-white' : 'border-slate-300 bg-white text-slate-700 hover:border-brand-500 hover:text-brand-700'}`}>{t(label)}</button>)}
    </div>
    <ErrorNote error={error} />
    <div className="card">
      {!rows ? <SkeletonRows cols={4} /> : rows.length === 0 ? <EmptyState icon={FileText} title={t('No events here yet')} /> :
        <ol className="divide-y divide-slate-100">
          {rows.map((r) => {
            const [Icon, tone, describe] = EVENTS[r.action] || [FileText, 'slate', () => [r.action, r.action]]
            return <li key={r.id} className="flex items-start gap-3 px-4 py-3">
              <div className={`mt-0.5 rounded-lg p-1.5 ${TONES[tone]}`}><Icon size={15} /></div>
              <div className="min-w-0 flex-1 text-sm">
                <div className="text-slate-800"><span className="font-medium">{r.user || t('system')}</span> {describe(r.details)[hi ? 1 : 0]}
                  {r.entity_type && !r.action.startsWith('auth.') && <> · <Subject r={r} hi={hi} /></>}</div>
                {r.details?.changes?.length > 0 && <div className="mt-0.5 text-xs text-slate-600">
                  {r.details.changes.map((c) => c.rejected ? `${fieldName(c.field)} ${t('rejected')}` : `${fieldName(c.field)}: ${c.from ?? '—'} → ${c.to}`).join(' · ')}</div>}
                <div className="mt-0.5 text-xs text-slate-500">
                  <time dateTime={r.ts} title={parseTs(r.ts).toLocaleString(locale())}>{ago(r.ts, hi)}</time>{r.ip && ` · ${r.ip}`}
                  <span className="ml-2 font-mono text-[10px] text-slate-500">{r.action}</span></div>
              </div>
            </li>
          })}
        </ol>}
      {total > 50 && <div className="flex items-center justify-end gap-2 border-t border-slate-100 p-3 text-sm">
        <button className="btn-outline py-1" disabled={page <= 1} onClick={() => setPage(page - 1)}>{t('Previous')}</button>
        <span className="text-slate-500">{t('Page')} {page} / {Math.ceil(total / 50)}</span>
        <button className="btn-outline py-1" disabled={page * 50 >= total} onClick={() => setPage(page + 1)}>{t('Next')}</button>
      </div>}
    </div>
  </div>
}
