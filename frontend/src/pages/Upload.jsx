import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Camera, CheckCircle2, ClipboardCheck, FileText, FileUp, Focus, Loader2, Maximize, Sun, XCircle } from 'lucide-react'
import { api } from '../api'
import { useAuth } from '../auth'
import { ConfidenceBar, PageHeader, StatusBadge, worstQuality } from '../components/ui'
import { useT } from '../i18n'
import { explainAdvice } from '../reasons'
import { useToast } from '../components/toast'

const ACCEPT = '.png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp,.pdf'
const DONE = ['auto_accepted', 'needs_review', 'verified', 'rejected', 'failed']

// Checked before sending, so the operator gets a clear message at once instead of a server
// error; the server still enforces both (backend/api/config.py MAX_UPLOAD_MB, ALLOWED_EXTENSIONS).
const MAX_MB = 20
const EXTS = ACCEPT.split(',')
function fileProblem(file) {
  const ext = file.name.includes('.') ? file.name.slice(file.name.lastIndexOf('.')).toLowerCase() : ''
  if (!EXTS.includes(ext)) return 'This file type is not supported. Use PDF, JPG, PNG or TIFF.'
  if (file.size > MAX_MB * 1024 * 1024) return 'File is larger than 20 MB. Scan at a lower resolution or split the PDF.'
  return null
}

const STEPS = ['Uploaded', 'In queue', 'Reading and checking', 'Done']
const TIPS = [
  [Maximize, 'Lay the page flat and fit the whole page in the frame'],
  [Sun, 'Use even daylight; avoid shadows and camera flash glare'],
  [Focus, 'Hold steady and tap the screen to focus before taking the photo'],
  [FileText, 'Best of all: a PDF downloaded from the land portal is read instantly and exactly'],
]

// Where one upload is: driven by the document's real status (queued / processing / done).
function Stepper({ status, started }) {
  const { t } = useT()
  const [, tick] = useState(0)
  useEffect(() => { const i = setInterval(() => tick((n) => n + 1), 1000); return () => clearInterval(i) }, [])
  const active = status === 'queued' ? 1 : status === 'processing' ? 2 : 3
  const secs = Math.max(0, Math.round((Date.now() - started) / 1000))
  return <ol className="my-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs" aria-label="progress">
    {STEPS.map((s, i) => <li key={s} className="flex items-center gap-2">
      <span className={`flex h-5 items-center gap-1.5 rounded-full px-2 ${i < active ? 'bg-emerald-50 text-ok' : i === active ? 'bg-brand-50 font-medium text-brand-700' : 'text-slate-500'}`}>
        {i < active ? <CheckCircle2 size={12} /> : i === active ? <Loader2 size={12} className="animate-spin" /> : <span className="h-1.5 w-1.5 rounded-full bg-slate-300" />}
        {t(s)}{i === active && i === 2 && <span className="tabular-nums text-slate-500"> · {secs}s</span>}
      </span>
      {i < STEPS.length - 1 && <span className={`h-px w-4 ${i < active ? 'bg-ok' : 'bg-slate-300'}`} />}
    </li>)}
  </ol>
}

export default function UploadPage() {
  const { t, lang } = useT()
  const { can } = useAuth()
  const toast = useToast()
  const [items, setItems] = useState([]) // {key, file, doc, error}
  const [drag, setDrag] = useState(false)
  const fileRef = useRef()
  const camRef = useRef()

  const add = async (files) => {
    for (const file of files) {
      const key = `${file.name}-${file.size}-${Math.random()}`
      const problem = fileProblem(file)
      if (problem) {
        setItems((xs) => [{ key, file, doc: null, error: t(problem), started: Date.now() }, ...xs])
        continue
      }
      setItems((xs) => [{ key, file, doc: null, error: null, started: Date.now() }, ...xs])
      try {
        const doc = await api.upload(file)
        setItems((xs) => xs.map((x) => (x.key === key ? { ...x, doc } : x)))
      } catch (e) {
        const dupId = e.detail?.document_id
        setItems((xs) => xs.map((x) => (x.key === key ? { ...x, error: e.message, dupId } : x)))
        toast(`${file.name}: ${t(dupId ? 'already uploaded' : 'could not be uploaded')}`, { type: dupId ? 'info' : 'error', body: e.message })
      }
    }
  }

  // poll documents still processing
  useEffect(() => {
    const pending = items.filter((x) => x.doc && !DONE.includes(x.doc.status))
    if (!pending.length) return
    const t = setTimeout(async () => {
      const updates = await Promise.all(pending.map((x) => api.document(x.doc.id).catch(() => null)))
      setItems((xs) => xs.map((x) => {
        const u = updates.find((d) => d && x.doc && d.id === x.doc.id)
        return u ? { ...x, doc: u } : x
      }))
    }, 1500)
    return () => clearTimeout(t)
  }, [items])

  // paste a screenshot or a copied file straight onto the page (Ctrl+V)
  useEffect(() => {
    const onPaste = (e) => {
      const files = [...(e.clipboardData?.files || [])].filter((f) => f.type.startsWith('image/') || f.type === 'application/pdf')
      if (!files.length) return
      e.preventDefault()
      // browsers name every pasted screenshot "image.png"; give each its own name
      add(files.map((f, i) => (f.name && f.name !== 'image.png' ? f : new File([f], `pasted-${Date.now()}-${i + 1}.png`, { type: f.type }))))
    }
    window.addEventListener('paste', onPaste)
    return () => window.removeEventListener('paste', onPaste)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // warn before leaving only while a file is still being sent; once the server has it,
  // processing carries on without this page
  const sending = items.some((x) => !x.error && !x.doc)
  useEffect(() => {
    if (!sending) return
    const warn = (e) => { e.preventDefault(); e.returnValue = '' }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [sending])

  // batch summary, so an operator with a stack of files sees at a glance what needs attention
  const finished = items.filter((x) => x.error || (x.doc && DONE.includes(x.doc.status)))
  const tally = {
    auto: finished.filter((x) => x.doc?.status === 'auto_accepted').length,
    review: finished.filter((x) => x.doc?.status === 'needs_review').length,
    retake: finished.filter((x) => x.doc && worstQuality(x.doc.pages)?.verdict === 'poor').length,
    dup: finished.filter((x) => x.dupId).length,
    failed: finished.filter((x) => (x.error && !x.dupId) || x.doc?.status === 'failed').length,
  }
  const showSummary = finished.length >= 2

  return <div>
    <PageHeader title={t('Upload land records')} subtitle={t('Scanned PDFs, images or phone photos · Hindi and English · printed or handwritten')} />
    <div className="grid gap-4 lg:grid-cols-[1fr_300px]">
    <div
      onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => { e.preventDefault(); setDrag(false); add([...e.dataTransfer.files]) }}
      className={`card border-2 border-dashed p-8 sm:p-12 text-center transition ${drag ? 'border-brand-500 bg-brand-50' : 'border-slate-300'}`}>
      <FileUp className="mx-auto text-brand-600" size={40} />
      <p className="mt-3 font-medium text-slate-800">{t('Drop files here')}</p>
      <p className="text-sm text-slate-500">{t('PNG, JPG, TIFF or PDF, up to 20 MB each')}</p>
      <p className="mt-1 hidden text-xs text-slate-500 sm:block">{t('or paste a screenshot with Ctrl+V')}</p>
      <div className="mt-5 flex flex-wrap justify-center gap-2">
        <button className="btn-primary" onClick={() => fileRef.current.click()}><FileUp size={16} /> {t('Choose files')}</button>
        <button className="btn-outline sm:hidden" onClick={() => camRef.current.click()}><Camera size={16} /> {t('Take photo')}</button>
      </div>
      <input ref={fileRef} type="file" multiple accept={ACCEPT} hidden onChange={(e) => { add([...e.target.files]); e.target.value = '' }} />
      <input ref={camRef} type="file" accept="image/*" capture="environment" hidden onChange={(e) => { add([...e.target.files]); e.target.value = '' }} />
    </div>
    <aside className="card p-4" aria-label={t('Tips for a good photo')}>
      <div className="font-medium text-slate-900">{t('Tips for a good photo')}</div>
      <ul className="mt-3 space-y-3 text-sm">
        {TIPS.map(([Icon, tip]) => <li key={tip} className="flex gap-2.5"><Icon size={16} className="mt-0.5 shrink-0 text-brand-600" /><span className="text-slate-700">{t(tip)}</span></li>)}
      </ul>
    </aside>
    </div>

    {showSummary && <div className="card mt-6 flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3 text-sm" role="status">
      <span className="font-medium text-slate-900">{finished.length}/{items.length} {t('files done')}</span>
      {tally.auto > 0 && <span className="inline-flex items-center gap-1.5 text-ok"><CheckCircle2 size={15} /> {tally.auto} {t('accepted automatically')}</span>}
      {tally.review > 0 && <span className="inline-flex items-center gap-1.5 text-warn"><ClipboardCheck size={15} /> {tally.review} {t('sent to a verifier')}</span>}
      {tally.retake > 0 && <span className="inline-flex items-center gap-1.5 text-bad"><Camera size={15} /> {tally.retake} {t('need a retake')}</span>}
      {tally.dup > 0 && <span className="inline-flex items-center gap-1.5 text-slate-600"><FileText size={15} /> {tally.dup} {t('already uploaded')}</span>}
      {tally.failed > 0 && <span className="inline-flex items-center gap-1.5 text-bad"><XCircle size={15} /> {tally.failed} {t('failed')}</span>}
      {/* a verifier who just uploaded a batch can go straight to what needs checking */}
      {tally.review > 0 && can('verifier') && <Link to="/review" className="ml-auto font-medium text-brand-700 hover:underline">{t('Review them')} →</Link>}
    </div>}
    {items.length > 0 && <div className={`card ${showSummary ? 'mt-3' : 'mt-6'} divide-y divide-slate-100`}>
      {/* an operator working through a stack can clear finished rows and carry on */}
      <div className="flex items-center justify-between px-4 py-2 text-xs text-slate-500">
        <span>{items.length} {t(items.length === 1 ? 'file' : 'files')}</span>
        <button className="btn-ghost py-1 text-xs" disabled={sending} onClick={() => setItems([])}>{t('Clear list')}</button>
      </div>
      {items.map((x) => {
        const d = x.doc
        const done = d && DONE.includes(d.status)
        return <div key={x.key} className="flex flex-wrap items-center gap-3 px-4 py-3">
          <div className="w-5">
            {x.error ? (x.dupId ? <FileText className="text-slate-500" size={18} /> : <XCircle className="text-bad" size={18} />)
              : done ? (d.status === 'failed' ? <XCircle className="text-bad" size={18} /> : <CheckCircle2 className="text-ok" size={18} />)
                : <Loader2 className="animate-spin text-brand-600" size={18} />}
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium">{x.file.name}</div>
            {d && !done && <Stepper status={d.status} started={x.started} />}
            <div className="text-xs text-slate-500">
              {/* a duplicate is not a failure: the file is already on record, so say so plainly and link to it */}
              {x.dupId ? <span className="text-slate-600">{t('already uploaded')} — <Link className="underline" to={`/documents/${x.dupId}`}>{t('open existing')}</Link></span>
                : x.error ? <span className="text-bad">{x.error}</span>
                : !d ? t('Uploading…')
                  : !done ? t('usually 10–30 seconds per page; digital PDFs about a second')
                    : d.status === 'failed' ? t('Could not process this file')
                      : `${d.district || t('Unknown district')} · ${t('processed in')} ${((d.processing_ms || 0) / 1000).toFixed(1)} s`}
            </div>
            {done && worstQuality(d.pages)?.verdict === 'poor' &&
              <div className="mt-1 flex items-start gap-1.5 text-xs font-medium text-bad">
                <Camera size={14} className="mt-0.5 shrink-0" />
                <span>{t('Image too poor to read reliably — please retake')}: {worstQuality(d.pages).advice.map((a) => explainAdvice(a, lang)).join('; ')}</span>
              </div>}
          </div>
          {d && <StatusBadge status={d.status} />}
          {done && d.overall_confidence != null && <ConfidenceBar value={d.overall_confidence} />}
          {done && <Link to={`/documents/${d.id}`} className="btn-outline py-1.5">{t('Open')}</Link>}
        </div>
      })}
    </div>}
  </div>
}
