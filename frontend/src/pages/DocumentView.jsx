import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { AlertTriangle, ArrowLeft, Check, CheckCircle2, Copy, History, Info, MapPin, RotateCcw, X, ZoomIn, ZoomOut } from 'lucide-react'
import { api } from '../api'
import { useAuth } from '../auth'
import { ConfidenceBar, confColor, ErrorNote, fmtDate, Spinner, StatusBadge, useAuthImage } from '../components/ui'
import { FIELDS, LAND_CLASSES } from '../constants'

const SOURCE_LABEL = { same_line: 'same line', near_right: 'beside label', below: 'table cell', inferred: 'inferred from master data', learned: 'learned correction', manual: 'entered by verifier' }

function PageImage({ doc, page, fields, selected, onSelect, threshold }) {
  const url = useAuthImage(() => api.pageBlob(doc.id, page.page), [doc.id, page.page, doc.processed_at])
  const [zoom, setZoom] = useState(1)
  const boxes = fields.filter((f) => f.bbox && (f.page || 1) === page.page)
  return <div className="card overflow-hidden">
    <div className="flex items-center justify-between border-b border-slate-100 px-3 py-2 text-xs text-slate-500">
      <span>Page {page.page} · deskew {page.preprocess?.deskew_angle ?? 0}° · {page.preprocess?.steps?.join(' → ')}</span>
      <div className="flex gap-1">
        <button className="btn-ghost p-1" onClick={() => setZoom((z) => Math.max(1, z - 0.5))} aria-label="zoom out"><ZoomOut size={15} /></button>
        <button className="btn-ghost p-1" onClick={() => setZoom((z) => Math.min(3, z + 0.5))} aria-label="zoom in"><ZoomIn size={15} /></button>
      </div>
    </div>
    <div className="max-h-[78vh] overflow-auto bg-slate-100">
      {!url ? <div className="flex h-96 items-center justify-center"><Spinner /></div> :
        <div className="relative" style={{ width: `${zoom * 100}%` }}>
          <img src={url} alt={`page ${page.page}`} className="block w-full select-none" draggable={false} />
          {boxes.map((f) => {
            const [x0, y0, x1, y1] = f.bbox
            const c = f.status === 'corrected' || f.status === 'confirmed' ? 1 : f.confidence
            const col = c >= threshold ? '21,128,61' : c >= threshold - 0.2 ? '180,83,9' : '185,28,28'
            const active = selected === f.name
            return <button key={f.name} title={`${f.name}: ${f.value ?? ''}`} onClick={() => onSelect(f.name)}
              className="absolute rounded-sm transition"
              style={{
                left: `${(x0 / page.width) * 100}%`, top: `${(y0 / page.height) * 100}%`,
                width: `${((x1 - x0) / page.width) * 100}%`, height: `${((y1 - y0) / page.height) * 100}%`,
                border: `2px solid rgba(${col},${active ? 1 : 0.7})`, background: `rgba(${col},${active ? 0.22 : 0.08})`,
                boxShadow: active ? `0 0 0 4px rgba(${col},0.25)` : 'none',
              }} />
          })}
        </div>}
    </div>
  </div>
}

function FieldRow({ def, f, decision, onDecision, editable, threshold, selected, onSelect }) {
  const ref = useRef()
  useEffect(() => { if (selected) ref.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }) }, [selected])
  const d = decision || {}
  const value = d.action === 'correct' ? d.value : (f?.value ?? '')
  const display = def.name === 'land_classification' && LAND_CLASSES[value] ? LAND_CLASSES[value] : null
  const hi = f?.normalized?.hi
  const low = f && f.status === 'pending' && (f.confidence < threshold || !f.valid)
  const reviewedTag = f && ['confirmed', 'corrected', 'rejected', 'auto'].includes(f.status) ? f.status : null

  return <div ref={ref} onClick={() => onSelect(def.name)}
    className={`px-4 py-3 border-b border-slate-100 cursor-pointer ${selected ? 'bg-brand-50' : low ? 'bg-amber-50/50' : ''}`}>
    <div className="flex items-center justify-between gap-2">
      <div className="text-xs font-medium text-slate-500">
        {def.en} <span className="text-slate-400">· {def.hi}</span>{def.required && <span className="text-bad"> *</span>}
      </div>
      <div className="flex items-center gap-2">
        {reviewedTag && <span className="text-[11px] rounded bg-slate-100 px-1.5 py-0.5 text-slate-600">{reviewedTag}</span>}
        {f && <ConfidenceBar value={f.status === 'corrected' ? 1 : f.confidence} threshold={threshold} />}
      </div>
    </div>
    <div className="mt-1.5 flex items-center gap-2">
      {editable ? (
        def.name === 'land_classification' ? (
          <select className={`input ${d.action === 'reject' ? 'line-through opacity-50' : ''}`} value={value || ''}
            onChange={(e) => onDecision({ action: 'correct', value: e.target.value })}>
            <option value="">—</option>
            {Object.entries(LAND_CLASSES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        ) : (
          <input className={`input ${d.action === 'reject' ? 'line-through opacity-50' : ''} ${d.action === 'correct' ? 'border-brand-500 bg-brand-50' : ''}`}
            value={value || ''} placeholder={f ? '' : 'not found — type to add'}
            onChange={(e) => onDecision(e.target.value === (f?.value ?? '') ? null : { action: 'correct', value: e.target.value })} />
        )
      ) : (
        <div className={`text-sm font-medium ${f?.status === 'rejected' ? 'line-through text-slate-400' : 'text-slate-900'}`}>
          {display || value || <span className="text-slate-400 font-normal">not found</span>}
          {hi && <span className="ml-2 font-normal text-slate-500">{hi}</span>}
        </div>
      )}
      {editable && f && <>
        <button title="Confirm" onClick={(e) => { e.stopPropagation(); onDecision(d.action === 'confirm' ? null : { action: 'confirm' }) }}
          className={`rounded-md p-1.5 ${d.action === 'confirm' ? 'bg-ok text-white' : 'text-slate-400 hover:bg-emerald-50 hover:text-ok'}`}><Check size={16} /></button>
        <button title="Reject this field" onClick={(e) => { e.stopPropagation(); onDecision(d.action === 'reject' ? null : { action: 'reject' }) }}
          className={`rounded-md p-1.5 ${d.action === 'reject' ? 'bg-bad text-white' : 'text-slate-400 hover:bg-red-50 hover:text-bad'}`}><X size={16} /></button>
      </>}
    </div>
    {f && <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-[11px] text-slate-500">
      {f.raw_value && <span>OCR read: <span className="font-mono text-slate-700">{f.raw_value}</span></span>}
      {f.source && <span>from {SOURCE_LABEL[f.source] || f.source}</span>}
      {f.ocr_confidence != null && <span>OCR {Math.round(f.ocr_confidence * 100)}%</span>}
      {f.original_value && f.status === 'corrected' && <span>was: {f.original_value}</span>}
    </div>}
    {f?.issues?.length > 0 && <div className="mt-1 flex flex-wrap gap-1">
      {f.issues.map((i) => <span key={i} className="rounded bg-amber-100 px-1.5 py-0.5 text-[11px] text-amber-800">{i}</span>)}
    </div>}
  </div>
}

export default function DocumentView() {
  const { id } = useParams()
  const nav = useNavigate()
  const { can } = useAuth()
  const [doc, setDoc] = useState(null)
  const [error, setError] = useState(null)
  const [decisions, setDecisions] = useState({})
  const [selected, setSelected] = useState(null)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [trail, setTrail] = useState(null)

  const load = () => api.document(id).then((d) => { setDoc(d); setError(null) }).catch(setError)
  useEffect(() => { setDoc(null); setDecisions({}); setNote(''); setTrail(null); load() }, [id]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!doc || !['queued', 'processing'].includes(doc.status)) return
    const t = setTimeout(load, 1500)
    return () => clearTimeout(t)
  }, [doc]) // eslint-disable-line react-hooks/exhaustive-deps

  const byName = useMemo(() => Object.fromEntries((doc?.fields || []).map((f) => [f.name, f])), [doc])
  const threshold = doc?.threshold ?? 0.8
  const editable = doc && can('verifier') && ['needs_review', 'auto_accepted'].includes(doc.status)

  if (error) return <ErrorNote error={error} />
  if (!doc) return <div className="flex justify-center p-16"><Spinner /></div>

  const setDecision = (name, dec) => setDecisions((ds) => { const n = { ...ds }; if (dec) n[name] = dec; else delete n[name]; return n })
  const flagged = FIELDS.filter((d) => byName[d.name] && byName[d.name].status === 'pending' && (byName[d.name].confidence < threshold || !byName[d.name].valid))
  const submit = async (decision) => {
    setBusy(true)
    setError(null)
    try {
      await api.verify(doc.id, { decision, fields: decisions, note: note || null })
      if (can('verifier')) {
        const q = await api.queue().catch(() => [])
        const next = q.find((d) => d.id !== doc.id)
        if (next) return nav(`/documents/${next.id}`)
      }
      setDecisions({})
      await load()
    } catch (e) { setError(e) } finally { setBusy(false) }
  }
  const loadTrail = () => api.audit({ entity_type: 'document', entity_id: doc.id }).then((r) => setTrail(r.items)).catch(setError)

  const processing = ['queued', 'processing'].includes(doc.status)
  return <div>
    <div className="mb-4 flex flex-wrap items-center gap-3">
      <button className="btn-ghost px-2" onClick={() => nav(-1)}><ArrowLeft size={16} /></button>
      <div className="min-w-0 flex-1">
        <h1 className="truncate text-lg font-semibold text-slate-900">{doc.filename}</h1>
        <div className="text-xs text-slate-500">#{doc.id} · {doc.document_type?.replaceAll('_', ' ') || 'unknown type'} · uploaded by {doc.uploader_name} · {fmtDate(doc.created_at)}
          {doc.processing_ms && <> · processed in {(doc.processing_ms / 1000).toFixed(1)} s</>}</div>
      </div>
      <StatusBadge status={doc.status} />
      {doc.overall_confidence != null && <ConfidenceBar value={doc.overall_confidence} threshold={threshold} />}
      {doc.record_id && <Link to={`/records?focus=${doc.record_id}`} className="btn-outline py-1.5"><MapPin size={15} /> Record #{doc.record_id}</Link>}
      {can() && !['verified', 'rejected'].includes(doc.status) && !processing &&
        <button className="btn-outline py-1.5" onClick={() => api.reprocess(doc.id).then(load)}><RotateCcw size={15} /> Re-run</button>}
    </div>

    {processing && <div className="card flex items-center gap-3 p-6"><Spinner /> Reading the document: preprocessing, OCR and field extraction. This takes a few seconds per page…</div>}
    {doc.status === 'failed' && <ErrorNote error={doc.error || 'processing failed'} />}

    {!processing && doc.status !== 'failed' && <>
      {(doc.route_reasons?.length > 0 || doc.duplicates?.length > 0 || doc.consistency?.some((c) => !c.ok)) && doc.status === 'needs_review' &&
        <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          <div className="flex items-center gap-2 font-medium"><AlertTriangle size={16} /> Why this needs a human</div>
          <ul className="mt-1 list-disc pl-6 text-[13px]">{doc.route_reasons.slice(0, 8).map((r) => <li key={r}>{r}</li>)}</ul>
        </div>}
      {doc.duplicates?.length > 0 && <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-900">
        <div className="flex items-center gap-2 font-medium"><Copy size={16} /> Possible duplicate of existing record</div>
        {doc.duplicates.map((d) => <div key={d.record_id} className="text-[13px] mt-1">Record #{d.record_id} — score {Math.round(d.score * 100)}% ({d.reasons.join(', ')})</div>)}
      </div>}
      {doc.status === 'auto_accepted' && <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900 flex items-center gap-2">
        <CheckCircle2 size={16} /> Every field passed validation with confidence above {Math.round(threshold * 100)}% — accepted without manual review. Verifiers can still audit and correct it.
      </div>}

      <div className="grid gap-4 lg:grid-cols-[1.15fr_1fr]">
        <div className="space-y-4">
          {doc.pages.map((p) => <PageImage key={p.page} doc={doc} page={p} fields={doc.fields} selected={selected} onSelect={setSelected} threshold={threshold} />)}
        </div>
        <div className="card flex flex-col lg:max-h-[86vh]">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <div className="font-medium">Extracted fields</div>
            <div className="text-xs text-slate-500">{flagged.length} flagged · auto-accept ≥ {Math.round(threshold * 100)}%</div>
          </div>
          <div className="flex-1 overflow-y-auto">
            {FIELDS.map((def) => (byName[def.name] || editable) &&
              <FieldRow key={def.name} def={def} f={byName[def.name]} decision={decisions[def.name]} editable={editable}
                onDecision={(dec) => setDecision(def.name, dec)} threshold={threshold} selected={selected === def.name} onSelect={setSelected} />)}
            {doc.consistency?.length > 0 && <div className="px-4 py-3 text-xs text-slate-600">
              <div className="label flex items-center gap-1"><Info size={12} /> Master data checks</div>
              {doc.consistency.map((c) => <div key={c.check} className={c.ok ? 'text-ok' : 'text-bad'}>{c.ok ? '✓' : '✗'} {c.check.replaceAll('_', ' ')} — {c.detail}</div>)}
            </div>}
          </div>
          {editable && <div className="border-t border-slate-100 p-3 space-y-2">
            <textarea className="input" rows={2} placeholder="Note for the audit trail (optional)" value={note} onChange={(e) => setNote(e.target.value)} />
            <ErrorNote error={error} />
            <div className="flex gap-2">
              <button className="btn-ok flex-1" disabled={busy} onClick={() => submit('approve')}><CheckCircle2 size={16} /> Approve record</button>
              <button className="btn-danger" disabled={busy} onClick={() => submit('reject')}><X size={16} /> Reject</button>
            </div>
            <div className="text-[11px] text-slate-500">Unmarked fields are confirmed as shown. Corrections are remembered and applied to future documents.</div>
          </div>}
          {!editable && doc.review_note && <div className="border-t border-slate-100 p-3 text-sm"><span className="label">Reviewer note</span>{doc.review_note}</div>}
        </div>
      </div>

      <div className="mt-4 card p-4">
        <button className="btn-ghost px-0 text-sm" onClick={loadTrail}><History size={15} /> Audit trail for this document</button>
        {trail && <ul className="mt-2 space-y-1 text-sm">
          {trail.map((t) => <li key={t.id} className="flex gap-3"><span className="text-slate-400 w-32 shrink-0">{fmtDate(t.ts)}</span>
            <span className="font-medium">{t.user}</span><span className="text-slate-600">{t.action}</span>
            {t.details?.changes?.length > 0 && <span className="text-slate-500">{t.details.changes.map((c) => c.field).join(', ')}</span>}
            {t.details?.route && <span className={confColor(t.details.confidence, threshold)}>{t.details.route} ({Math.round((t.details.confidence || 0) * 100)}%)</span>}
          </li>)}
        </ul>}
      </div>
    </>}
  </div>
}
