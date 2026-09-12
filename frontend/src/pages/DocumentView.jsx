import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { AlertTriangle, ArrowLeft, Camera, Check, CheckCircle2, Copy, History, Info, LayoutList, MapPin, RotateCcw, Users, X, ZoomIn, ZoomOut } from 'lucide-react'
import { api } from '../api'
import { useAuth } from '../auth'
import { ConfidenceBar, confColor, ErrorNote, fmtDate, QualityBadge, Spinner, StatusBadge, useAuthImage, worstQuality } from '../components/ui'
import { docTypeLabel, FIELDS, LAND_CLASSES } from '../constants'
import { useT } from '../i18n'
import { explainAdvice, explainDuplicateReason, explainIssue, explainReason } from '../reasons'
import { useToast } from '../components/toast'
import { getQueueOrder, sortQueue } from '../queue'

// preprocessing steps (backend/ocr/preprocess.py) as shown to a Hindi reader; English shows the step names
const STEP_HI = { grayscale: 'धूसर', resize: 'आकार बदला', page_crop: 'पन्ना काटा', illumination: 'रोशनी समतल', rotate90: '90° घुमाया',
  rotate180: 'उल्टा सीधा किया', deskew: 'तिरछापन ठीक', denoise: 'शोर हटाया', sharpen: 'धार बढ़ाई', clahe: 'कंट्रास्ट बढ़ाया',
  binarize: 'श्वेत-श्याम', table_cells: 'तालिका के खाने', 'second read': 'दूसरी बार पढ़ा', numbers: 'अंक फिर पढ़े' }
const stepLabel = (s, lang) => {
  if (lang !== 'hi') return s
  if (STEP_HI[s]) return STEP_HI[s]            // whole step name (e.g. "second read")
  const [k, n] = s.split(/[: ]/)
  return STEP_HI[k] ? `${STEP_HI[k]}${n ? ` ${n}` : ''}` : s
}

// "numbers:3" in the steps: how many number tokens were read a second time
export const numbersReread = (page) =>
  Number(page.preprocess?.steps?.find((s) => s.startsWith('numbers:'))?.split(':')[1] || 0)

const SOURCE_LABEL = { same_line: 'same line', near_right: 'beside label', below: 'table cell', inferred: 'inferred from master data', learned: 'learned correction', manual: 'entered by verifier' }

function PageImage({ doc, page, fields, selected, onSelect, threshold }) {
  const { t, lang } = useT()
  const url = useAuthImage(() => api.pageBlob(doc.id, page.page), [doc.id, page.page, doc.processed_at])
  const [zoom, setZoom] = useState(1)
  const boxes = fields.filter((f) => f.bbox && (f.page || 1) === page.page)
  const fieldLabel = (n) => FIELDS.find((d) => d.name === n)?.[lang === 'hi' ? 'hi' : 'en'] || n
  return <div className="card overflow-hidden">
    <div className="flex items-center justify-between border-b border-slate-100 px-3 py-2 text-xs text-slate-500">
      <span className="flex flex-wrap items-center gap-2">
        <span>{t('Page')} {page.page}</span>
        <QualityBadge quality={page.quality} />
        {/* the page read badly the first time, so the pipeline read it again */}
        {page.preprocess?.steps?.includes('second read') &&
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600"
            title={t('This page read badly, so it was read again with lighter denoising')}>{t('read twice')}</span>}
        {/* numbers that read unsurely were read again by an english-only recogniser */}
        {numbersReread(page) > 0 &&
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600"
            title={t('Numbers that read unsurely were read again in English alone, where digits are not confused with Devanagari')}>
            {numbersReread(page)} {t(numbersReread(page) === 1 ? 'number read again' : 'numbers read again')}</span>}
        {page.preprocess?.steps?.includes('pdf_text_layer')
          ? <span>{t("read from the PDF's text layer (no OCR needed)")}</span>
          : <span>{lang === 'hi' ? 'तिरछापन' : 'deskew'} {page.preprocess?.deskew_angle ?? 0}° · {page.preprocess?.steps?.map((s) => stepLabel(s, lang)).join(' → ')}</span>}
      </span>
      <div className="flex items-center gap-1">
        {/* when zoomed in, the percentage doubles as a one-click way back to the whole page */}
        {zoom > 1 && <button className="btn-ghost px-1.5 py-0.5 text-[11px] tabular-nums" onClick={() => setZoom(1)} title={t('Fit to width')}>{Math.round(zoom * 100)}%</button>}
        <button className="btn-ghost p-1" onClick={() => setZoom((z) => Math.max(1, z - 0.5))} disabled={zoom <= 1}
          aria-label={t('Zoom out')} title={t('Zoom out')}><ZoomOut size={15} /></button>
        <button className="btn-ghost p-1" onClick={() => setZoom((z) => Math.min(3, z + 0.5))} disabled={zoom >= 3}
          aria-label={t('Zoom in')} title={t('Zoom in')}><ZoomIn size={15} /></button>
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
            return <button key={f.name} title={`${fieldLabel(f.name)}: ${f.value ?? ''}`} aria-label={`${fieldLabel(f.name)}: ${f.value ?? ''}`}
              onClick={() => onSelect(f.name)}
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
  const { t, lang } = useT()
  const ref = useRef()
  useEffect(() => { if (selected) ref.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }) }, [selected])
  const d = decision || {}
  const value = d.action === 'correct' ? d.value : (f?.value ?? '')
  const display = def.name === 'land_classification' && LAND_CLASSES[value] ? LAND_CLASSES[value] : null
  const hi = f?.normalized?.hi
  const low = f && f.status === 'pending' && (f.confidence < threshold || !f.valid)
  const reviewedTag = f && ['confirmed', 'corrected', 'rejected', 'auto'].includes(f.status) ? f.status : null

  return <div ref={ref} data-field-row={def.name} onClick={() => onSelect(def.name)}
    className={`px-4 py-3 border-b border-slate-100 cursor-pointer ${selected ? 'bg-brand-50' : low ? 'bg-amber-50/50' : ''}`}>
    <div className="flex items-center justify-between gap-2">
      <div className="text-xs font-medium text-slate-500">
        {def.en} <span className="text-slate-500">· {def.hi}</span>{def.required && <span className="text-bad"> *</span>}
      </div>
      <div className="flex items-center gap-2">
        {reviewedTag && <span className="text-[11px] rounded bg-slate-100 px-1.5 py-0.5 text-slate-600">{t(reviewedTag)}</span>}
        {f && <ConfidenceBar value={f.status === 'corrected' ? 1 : f.confidence} threshold={threshold} />}
      </div>
    </div>
    <div className="mt-1.5 flex items-center gap-2">
      {editable ? (
        def.name === 'land_classification' ? (
          <select className={`input ${d.action === 'reject' ? 'line-through opacity-50' : ''}`} value={value || ''}
            aria-label={lang === 'hi' ? def.hi : def.en}
            onChange={(e) => onDecision({ action: 'correct', value: e.target.value })}>
            <option value="">—</option>
            {Object.entries(LAND_CLASSES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        ) : (
          <input className={`input ${d.action === 'reject' ? 'line-through opacity-50' : ''} ${d.action === 'correct' ? 'border-brand-500 bg-brand-50' : ''}`}
            aria-label={lang === 'hi' ? def.hi : def.en}
            value={value || ''} placeholder={f ? '' : t('not found — type to add')}
            onChange={(e) => onDecision(e.target.value === (f?.value ?? '') ? null : { action: 'correct', value: e.target.value })} />
        )
      ) : (
        <div className={`text-sm font-medium ${f?.status === 'rejected' ? 'line-through text-slate-500' : 'text-slate-900'}`}>
          {display || value || <span className="text-slate-500 font-normal">{t('not found')}</span>}
          {hi && <span className="ml-2 font-normal text-slate-500">{hi}</span>}
        </div>
      )}
      {editable && f && <>
        <button title={t('Confirm')} aria-label={`${t('Confirm')}: ${lang === 'hi' ? def.hi : def.en}`} onClick={(e) => { e.stopPropagation(); onDecision(d.action === 'confirm' ? null : { action: 'confirm' }) }}
          className={`rounded-md p-1.5 ${d.action === 'confirm' ? 'bg-ok text-white' : 'text-slate-500 hover:bg-emerald-50 hover:text-ok'}`}><Check size={16} /></button>
        <button title={t('Reject this field')} aria-label={`${t('Reject')}: ${lang === 'hi' ? def.hi : def.en}`} onClick={(e) => { e.stopPropagation(); onDecision(d.action === 'reject' ? null : { action: 'reject' }) }}
          className={`rounded-md p-1.5 ${d.action === 'reject' ? 'bg-bad text-white' : 'text-slate-500 hover:bg-red-50 hover:text-bad'}`}><X size={16} /></button>
      </>}
    </div>
    {f && <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-[11px] text-slate-500">
      {f.raw_value && <span>{t('OCR read')}: <span className="font-mono text-slate-700">{f.raw_value}</span></span>}
      {f.source && <span>{t('from')} {t(SOURCE_LABEL[f.source] || f.source)}</span>}
      {f.ocr_confidence != null && <span>OCR {Math.round(f.ocr_confidence * 100)}%</span>}
      {f.original_value && f.status === 'corrected' && <span>{t('was')}: {f.original_value}</span>}
    </div>}
    {f?.issues?.length > 0 && <div className="mt-1 flex flex-wrap gap-1">
      {f.issues.map((i) => <span key={i} className="rounded bg-amber-100 px-1.5 py-0.5 text-[11px] text-amber-800" title={i}>{explainIssue(i, lang)}</span>)}
    </div>}
  </div>
}

export default function DocumentView() {
  const { t, lang } = useT()
  const toast = useToast()
  const { id } = useParams()
  const nav = useNavigate()
  const { can } = useAuth()
  const [doc, setDoc] = useState(null)
  const [error, setError] = useState(null)
  const [decisions, setDecisions] = useState({})
  // the browser tab names the document, so several open reviews can be told apart
  useEffect(() => { if (doc?.filename) document.title = `${doc.filename} · LandLekha` }, [doc?.filename])
  const [selected, setSelected] = useState(null)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [trail, setTrail] = useState(null)
  const [left, setLeft] = useState(null)
  const keyRef = useRef(null)
  // one listener for the page; it always calls the latest handler (set below, after data loads)
  useEffect(() => {
    const h = (e) => keyRef.current?.(e)
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [])

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
  useEffect(() => {
    if (!editable) return
    api.queue().then((q) => setLeft(q.filter((d) => d.id !== doc.id).length)).catch(() => {})
  }, [editable, doc?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  // Pending decisions are kept as a draft per document (for a day), so a reload, a closed tab or
  // a click elsewhere does not throw away a verifier's corrections. Saving starts only after the
  // saved draft has been read, so the reset on opening a document cannot wipe it first.
  const draftKey = `landlekha.draft.${id}`
  const restoredFor = useRef(null)
  useEffect(() => {
    if (!doc || String(doc.id) !== String(id) || restoredFor.current === id) return
    restoredFor.current = id
    if (!editable) return
    try {
      const saved = JSON.parse(localStorage.getItem(draftKey) || 'null')
      if (saved && Date.now() - saved.at < 86400000 && Object.keys(saved.decisions || {}).length) {
        setDecisions(saved.decisions)
        toast(t('Your unsaved changes were restored'), { type: 'info', body: t('Review them and approve when ready.') })
      }
    } catch { /* storage blocked or an unreadable draft */ }
  }, [doc, id]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (restoredFor.current !== id) return
    try {
      if (Object.keys(decisions).length) localStorage.setItem(draftKey, JSON.stringify({ at: Date.now(), decisions }))
      else localStorage.removeItem(draftKey)
    } catch { /* storage blocked */ }
  }, [decisions]) // eslint-disable-line react-hooks/exhaustive-deps

  if (error) return <ErrorNote error={error} />
  if (!doc) return <div className="flex justify-center p-16"><Spinner /></div>

  const setDecision = (name, dec) => setDecisions((ds) => { const n = { ...ds }; if (dec) n[name] = dec; else delete n[name]; return n })
  const flagged = FIELDS.filter((d) => byName[d.name] && byName[d.name].status === 'pending' && (byName[d.name].confidence < threshold || !byName[d.name].valid))
  // leave this document for later and open the next one in the chosen queue order;
  // any unsaved corrections here stay as a draft
  const skip = async () => {
    const q = await api.queue().catch(() => [])
    const next = sortQueue(q, getQueueOrder()).find((d) => d.id !== doc.id)
    if (next) nav(`/documents/${next.id}`)
  }
  const submit = async (decision) => {
    setBusy(true)
    setError(null)
    try {
      await api.verify(doc.id, { decision, fields: decisions, note: note || null })
      const nChanged = Object.values(decisions).filter((d) => d.action !== 'confirm').length
      toast(`${t(decision === 'approve' ? 'Record approved' : 'Document rejected')}: ${doc.filename}`,
        { body: decision === 'approve'
          ? (nChanged ? `${nChanged} ${t(nChanged > 1 ? 'corrections saved and learned' : 'correction saved and learned')}` : t('All fields confirmed as read'))
          : t('Kept in the audit trail with your note'),
          type: decision === 'approve' ? 'success' : 'info' })
      if (can('verifier')) {
        const q = await api.queue().catch(() => [])
        // the next document in the order the verifier chose on the queue page
        const next = sortQueue(q, getQueueOrder()).find((d) => d.id !== doc.id)
        if (next) return nav(`/documents/${next.id}`)
        if (decision === 'approve') toast(t('All clear'), { type: 'info', body: t('The review queue is empty. Nice work.') })
      }
      setDecisions({})
      await load()
    } catch (e) {
      // the backend refuses approval while required fields are empty: name them plainly and go to the first one
      const missing = String(e.message).match(/required fields missing: \[(.*)\]/)?.[1].match(/\w+/g)
      if (missing?.length) {
        const label = (n) => FIELDS.find((f) => f.name === n)?.[lang === 'hi' ? 'hi' : 'en'] || n
        toast(t('Could not save the review'), { type: 'error', body: `${t('Fill in these required fields first')}: ${missing.map(label).join(', ')}` })
        setSelected(missing[0])
      } else {
        setError(e)
        toast(t('Could not save the review'), { type: 'error', body: t(e.message) })
      }
    } finally { setBusy(false) }
  }
  // keyboard: arrows/j/k move, Enter confirm, X reject, E edit, Ctrl+Enter approve
  const present = FIELDS.filter((d) => byName[d.name] || editable).map((d) => d.name)
  keyRef.current = (e) => {
    if (!editable || busy) return
    const typing = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); submit('approve'); return }
    if (typing) { if (e.key === 'Escape') document.activeElement.blur(); return }
    const i = present.indexOf(selected)
    const move = (d) => { e.preventDefault(); setSelected(present[Math.min(present.length - 1, Math.max(0, (i < 0 ? -1 : i) + d))]) }
    if (e.key === 'n' || e.key === 'N') { e.preventDefault(); return nextFlagged() }
    if (e.key === 'ArrowDown' || e.key === 'j') return move(1)
    if (e.key === 'ArrowUp' || e.key === 'k') return move(-1)
    if (!selected) return
    if (e.key === 'Enter' && byName[selected]) { e.preventDefault(); setDecision(selected, decisions[selected]?.action === 'confirm' ? null : { action: 'confirm' }) }
    else if ((e.key === 'x' || e.key === 'X') && byName[selected]) { e.preventDefault(); setDecision(selected, decisions[selected]?.action === 'reject' ? null : { action: 'reject' }) }
    else if (e.key === 'e' || e.key === 'E') { e.preventDefault(); document.querySelector(`[data-field-row="${selected}"] input, [data-field-row="${selected}"] select`)?.focus() }
  }
  // flagged fields the verifier has not decided on yet, and a jump to the next one
  const open = flagged.filter((d) => !decisions[d.name]).map((d) => d.name)
  const nextFlagged = () => {
    if (!open.length) return
    const after = open.find((n) => FIELDS.findIndex((d) => d.name === n) > FIELDS.findIndex((d) => d.name === selected))
    setSelected(after || open[0])
  }
  const loadTrail = () => api.audit({ entity_type: 'document', entity_id: doc.id }).then((r) => setTrail(r.items)).catch(setError)

  const processing = ['queued', 'processing'].includes(doc.status)
  const quality = worstQuality(doc.pages)
  return <div>
    <div className="mb-4 flex flex-wrap items-center gap-3">
      <button className="btn-ghost px-2" onClick={() => nav(-1)} aria-label={t('Back')} title={t('Back')}><ArrowLeft size={16} /></button>
      {/* basis-60: on a phone the title keeps a usable width and the badges wrap below it */}
      <div className="min-w-0 flex-1 basis-60">
        <h1 className="truncate text-lg font-semibold text-slate-900">{doc.filename}</h1>
        <div className="text-xs text-slate-500">#{doc.id} · {docTypeLabel(doc.document_type, lang)} · {t('uploaded by')} {doc.uploader_name} · {fmtDate(doc.created_at)}
          {doc.processing_ms && <> · {t('processed in')} {(doc.processing_ms / 1000).toFixed(1)} s</>}</div>
      </div>
      <StatusBadge status={doc.status} />
      {doc.overall_confidence != null && <ConfidenceBar value={doc.overall_confidence} threshold={threshold} />}
      {/* the register is a verifier's screen, so an operator gets the number without a dead link */}
      {doc.record_id && (can('verifier')
        ? <Link to={`/records?focus=${doc.record_id}`} className="btn-outline py-1.5"><MapPin size={15} /> {t('Record')} #{doc.record_id}</Link>
        : <span className="text-sm text-slate-500">{t('Record')} #{doc.record_id}</span>)}
      {can() && !['verified', 'rejected'].includes(doc.status) && !processing &&
        <button className="btn-outline py-1.5" onClick={() => api.reprocess(doc.id).then(() => { toast(t('Processing again'), { type: 'info', body: t('The page will update when it is done') }); load() })}><RotateCcw size={15} /> {t('Re-run')}</button>}
      {/* an officer who spots something wrong after approval can reopen it - every field goes
          back to pending, exactly like a fresh review, rather than a one-off patch */}
      {can('verifier') && doc.status === 'verified' &&
        <button className="btn-outline py-1.5" onClick={async () => {
          const note = window.prompt(t('Why does this need another look?'))
          if (!note) return
          try {
            await api.dispute(doc.id, note)
            toast(t('Sent back for re-verification'), { type: 'info' })
            load()
          } catch (e) { toast(t('Could not save the review'), { type: 'error', body: t(e.message) }) }
        }}><AlertTriangle size={15} /> {t('Flag for re-verification')}</button>}
    </div>

    {processing && <div className="card flex items-center gap-3 p-6"><Spinner /> {t('Reading the document: preprocessing, OCR and field extraction. This takes a few seconds per page…')}</div>}
    {doc.status === 'failed' && <ErrorNote error={doc.error || 'processing failed'} />}

    {!processing && doc.status !== 'failed' && <>
      {quality && quality.verdict !== 'good' &&
        <div className={`mb-4 rounded-xl border p-3 text-sm ${quality.verdict === 'poor' ? 'border-red-200 bg-red-50 text-red-900' : 'border-amber-200 bg-amber-50 text-amber-900'}`}>
          <div className="flex items-center gap-2 font-medium"><Camera size={16} />
            {quality.verdict === 'poor' ? t('The image is too poor to read reliably — please rescan or retake it') : t('Image quality is only fair — check the flagged fields carefully')}</div>
          <ul className="mt-1 list-disc pl-6 text-[13px]">{quality.advice.map((a) => <li key={a}>{explainAdvice(a, lang)}</li>)}</ul>
        </div>}
      {/* nothing at all was recognised: usually the wrong page, not a bad scan. Saying so beats
          seven "missing required field" bullets. */}
      {doc.fields?.length === 0 && doc.status === 'needs_review' &&
        <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          <div className="flex items-center gap-2 font-medium"><AlertTriangle size={16} /> {t('No land-record fields were found on this page')}</div>
          <div className="mt-1 text-[13px]">{t('The page was read, but it does not look like a Khatauni, Khasra, Jamabandi or Record of Rights. Check that the right page was uploaded.')}</div>
        </div>}
      {doc.fields?.length > 0 && (doc.route_reasons?.length > 0 || doc.duplicates?.length > 0 || doc.consistency?.some((c) => !c.ok)) && doc.status === 'needs_review' &&
        <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          <div className="flex items-center gap-2 font-medium"><AlertTriangle size={16} /> {t('Why this needs a human')}</div>
          <ul className="mt-1 list-disc pl-6 text-[13px]">{doc.route_reasons.slice(0, 8).map((r) => <li key={r}>{explainReason(r, lang)}</li>)}</ul>
        </div>}
      {doc.duplicates?.length > 0 && <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-900">
        <div className="flex items-center gap-2 font-medium"><Copy size={16} /> {t('Possible duplicate of existing record')}</div>
        {doc.duplicates.map((d) => <div key={d.record_id} className="text-[13px] mt-1">
          {/* open the record it matches, so the two can be compared before anything is approved */}
          {can('verifier')
            ? <Link to={`/records?focus=${d.record_id}`} className="font-medium underline">{t('Record')} #{d.record_id}</Link>
            : <span className="font-medium">{t('Record')} #{d.record_id}</span>}
          {' — '}{t('match')} {Math.round(d.score * 100)}% ({d.reasons.map((r) => explainDuplicateReason(r, lang)).join(', ')})
        </div>)}
      </div>}
      {doc.status === 'auto_accepted' && <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900 flex items-center gap-2">
        <CheckCircle2 size={16} className="shrink-0" /> {lang === 'hi'
          ? `हर विवरण ${Math.round(threshold * 100)}% से अधिक विश्वसनीयता के साथ सभी जाँचों में सही निकला, इसलिए बिना मैन्युअल जाँच के स्वीकृत हुआ। जाँचकर्ता फिर भी इसे देख और सुधार सकते हैं।`
          : `Every field passed validation with confidence above ${Math.round(threshold * 100)}% — accepted without manual review. Verifiers can still audit and correct it.`}
      </div>}

      <div className="grid gap-4 lg:grid-cols-[1.15fr_1fr]">
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-1 text-xs text-slate-600" aria-label={t('box colours')}>
            <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-sm border-2 border-ok bg-emerald-50" /> {t('confident')}</span>
            <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-sm border-2 border-warn bg-amber-50" /> {t('please check')}</span>
            <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-sm border-2 border-bad bg-red-50" /> {t('probably wrong')}</span>
            <span className="text-slate-500">{t('click a box to jump to its field')}</span>
            {/* on phones the fields come after the whole scan; one tap gets there */}
            <button type="button" className="btn-outline min-h-8 px-2.5 py-1 text-xs lg:hidden"
              onClick={() => document.getElementById('fields')?.scrollIntoView({ behavior: 'smooth', block: 'start' })}>{t('Go to fields')} ↓</button>
          </div>
          {doc.pages.map((p) => <PageImage key={p.page} doc={doc} page={p} fields={doc.fields} selected={selected} onSelect={setSelected} threshold={threshold} />)}
        </div>
        <div id="fields" className="card flex scroll-mt-4 flex-col lg:max-h-[86vh]">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <div className="font-medium">{t('Extracted fields')}</div>
            <div className="text-xs text-slate-500">{flagged.length} {t('flagged')} · {t('auto-accept')} ≥ {Math.round(threshold * 100)}%</div>
          </div>
          {editable && flagged.length > 0 && <div className="flex items-center gap-3 border-b border-slate-100 px-4 py-2">
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-valuemin={0} aria-valuemax={flagged.length} aria-valuenow={flagged.length - open.length}>
              <div className="h-full rounded-full bg-ok transition-[width] duration-300" style={{ width: `${((flagged.length - open.length) / flagged.length) * 100}%` }} />
            </div>
            <span className="text-xs tabular-nums text-slate-600">{flagged.length - open.length}/{flagged.length} {t('checked')}</span>
            <button className="btn-outline min-h-8 px-2.5 py-1 text-xs" disabled={!open.length} onClick={nextFlagged}>{open.length ? t('Next flagged') : t('All flagged fields checked')}</button>
          </div>}
          {/* focusable so keyboard users can scroll it even when nothing inside is editable */}
          <div className="flex-1 overflow-y-auto" tabIndex={0} role="region" aria-label={t('Extracted fields')}>
            {FIELDS.map((def) => (byName[def.name] || editable) &&
              <FieldRow key={def.name} def={def} f={byName[def.name]} decision={decisions[def.name]} editable={editable}
                onDecision={(dec) => setDecision(def.name, dec)} threshold={threshold} selected={selected === def.name} onSelect={setSelected} />)}
            {doc.owners?.length > 1 && <div className="border-b border-slate-100 px-4 py-3">
              <div className="label flex items-center gap-1"><Users size={12} /> {t('Co-owners on this khata')} ({doc.owners.length})</div>
              <ol className="mt-1 space-y-0.5 text-sm">
                {doc.owners.map((o, i) => <li key={i}><span className="text-slate-500 tabular-nums">{i + 1}.</span> <span className="font-medium">{o.owner_name || '—'}</span>
                  {o.father_name && <span className="text-slate-500"> · {o.father_name}</span>}</li>)}
              </ol>
            </div>}
            {doc.parcels?.length > 1 && <div className="border-b border-slate-100 px-4 py-3">
              <div className="label flex items-center gap-1"><LayoutList size={12} /> {t('Parcels under this khata')} ({doc.parcels.length})</div>
              <table className="mt-1 w-full text-sm">
                <thead><tr className="text-left text-[11px] uppercase text-slate-500"><th className="py-1 font-medium">Khasra</th><th className="font-medium">Area</th><th className="font-medium">Class</th></tr></thead>
                <tbody>{doc.parcels.map((p, i) => <tr key={i} className="border-t border-slate-100">
                  <td className="py-1 tabular-nums">{p.khasra_number || '—'}</td>
                  <td className="tabular-nums">{p.plot_area || '—'}</td>
                  <td className="text-xs">{LAND_CLASSES[p.land_classification]?.split(' · ')[0] || p.land_classification || '—'}</td>
                </tr>)}</tbody>
              </table>
              <div className="mt-1 text-[11px] text-slate-500">{t('The fields above show the first row; correct individual rows on the scan if needed.')}</div>
            </div>}
            {doc.consistency?.length > 0 && <div className="px-4 py-3 text-xs text-slate-600">
              <div className="label flex items-center gap-1"><Info size={12} /> {t('Master data checks')}</div>
              {doc.consistency.map((c) => <div key={c.check} className={c.ok ? 'text-ok' : 'text-bad'}>{c.ok ? '✓' : '✗'} {c.check.replaceAll('_', ' ')} — {c.detail}</div>)}
            </div>}
          </div>
          {editable && <div className="border-t border-slate-100 p-3 space-y-2">
            <textarea className="input" rows={2} placeholder={t('Note for the audit trail (optional)')} value={note} onChange={(e) => setNote(e.target.value)} />
            <ErrorNote error={error} />
            <div className="flex gap-2">
              <button className="btn-ok flex-1" disabled={busy} onClick={() => submit('approve')}><CheckCircle2 size={16} /> {t('Approve record')}{left > 0 && <span className="font-normal"> · {left} {t('left')}</span>}</button>
              <button className="btn-danger" disabled={busy} onClick={() => submit('reject')}><X size={16} /> {t('Reject')}</button>
              {left > 0 && <button className="btn-outline" disabled={busy} onClick={skip}
                title={t('Leave this one for later; your changes stay as a draft')}>{t('Skip')}</button>}
            </div>
            <div className="hidden flex-wrap gap-x-3 text-[11px] text-slate-500 lg:flex" aria-label={t('keyboard shortcuts')}>
              <span><kbd className="kbd">↑</kbd><kbd className="kbd">↓</kbd> {t('move')}</span><span><kbd className="kbd">Enter</kbd> {t('confirm')}</span>
              <span><kbd className="kbd">N</kbd> {t('next flagged')}</span><span><kbd className="kbd">X</kbd> {t('reject field')}</span><span><kbd className="kbd">E</kbd> {t('edit')}</span>
              <span><kbd className="kbd">Ctrl</kbd>+<kbd className="kbd">Enter</kbd> {t('approve')}</span>
            </div>
            <div className="text-[11px] text-slate-500">{t('Unmarked fields are confirmed as shown. Corrections are remembered and applied to future documents.')}</div>
          </div>}
          {!editable && doc.review_note && <div className="border-t border-slate-100 p-3 text-sm"><span className="label">{t('Reviewer note')}</span>{doc.review_note}</div>}
        </div>
      </div>

      <div className="mt-4 card p-4">
        <button className="btn-ghost px-0 text-sm" onClick={loadTrail}><History size={15} /> {t('Audit trail for this document')}</button>
        {trail && <ul className="mt-2 space-y-1 text-sm">
          {trail.map((t) => <li key={t.id} className="flex gap-3"><span className="text-slate-500 w-32 shrink-0">{fmtDate(t.ts)}</span>
            <span className="font-medium">{t.user}</span><span className="text-slate-600">{t.action}</span>
            {t.details?.changes?.length > 0 && <span className="text-slate-500">{t.details.changes.map((c) => c.field).join(', ')}</span>}
            {t.details?.route && <span className={confColor(t.details.confidence, threshold)}>{t.details.route} ({Math.round((t.details.confidence || 0) * 100)}%)</span>}
          </li>)}
        </ul>}
      </div>
    </>}
  </div>
}
