import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Camera, CheckCircle2, FileUp, Loader2, XCircle } from 'lucide-react'
import { api } from '../api'
import { ConfidenceBar, PageHeader, StatusBadge, worstQuality } from '../components/ui'
import { useT } from '../i18n'
import { useToast } from '../components/toast'

const ACCEPT = '.png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp,.pdf'
const DONE = ['auto_accepted', 'needs_review', 'verified', 'rejected', 'failed']

const STEPS = ['Uploaded', 'In queue', 'Reading and checking', 'Done']

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
  const { t } = useT()
  const toast = useToast()
  const [items, setItems] = useState([]) // {key, file, doc, error}
  const [drag, setDrag] = useState(false)
  const fileRef = useRef()
  const camRef = useRef()

  const add = async (files) => {
    for (const file of files) {
      const key = `${file.name}-${file.size}-${Math.random()}`
      setItems((xs) => [{ key, file, doc: null, error: null, started: Date.now() }, ...xs])
      try {
        const doc = await api.upload(file)
        setItems((xs) => xs.map((x) => (x.key === key ? { ...x, doc } : x)))
      } catch (e) {
        const dupId = e.detail?.document_id
        setItems((xs) => xs.map((x) => (x.key === key ? { ...x, error: e.message, dupId } : x)))
        toast(dupId ? `${file.name} was already uploaded` : `${file.name} could not be uploaded`, { type: dupId ? 'info' : 'error', body: e.message })
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

  return <div>
    <PageHeader title={t('Upload land records')} subtitle={t('Scanned PDFs, images or phone photos · Hindi and English · printed or handwritten')} />
    <div
      onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => { e.preventDefault(); setDrag(false); add([...e.dataTransfer.files]) }}
      className={`card border-2 border-dashed p-8 sm:p-12 text-center transition ${drag ? 'border-brand-500 bg-brand-50' : 'border-slate-300'}`}>
      <FileUp className="mx-auto text-brand-600" size={40} />
      <p className="mt-3 font-medium text-slate-800">{t('Drop files here')}</p>
      <p className="text-sm text-slate-500">{t('PNG, JPG, TIFF or PDF, up to 20 MB each')}</p>
      <div className="mt-5 flex flex-wrap justify-center gap-2">
        <button className="btn-primary" onClick={() => fileRef.current.click()}><FileUp size={16} /> {t('Choose files')}</button>
        <button className="btn-outline sm:hidden" onClick={() => camRef.current.click()}><Camera size={16} /> {t('Take photo')}</button>
      </div>
      <input ref={fileRef} type="file" multiple accept={ACCEPT} hidden onChange={(e) => { add([...e.target.files]); e.target.value = '' }} />
      <input ref={camRef} type="file" accept="image/*" capture="environment" hidden onChange={(e) => { add([...e.target.files]); e.target.value = '' }} />
    </div>

    {items.length > 0 && <div className="card mt-6 divide-y divide-slate-100">
      {items.map((x) => {
        const d = x.doc
        const done = d && DONE.includes(d.status)
        return <div key={x.key} className="flex flex-wrap items-center gap-3 px-4 py-3">
          <div className="w-5">
            {x.error ? <XCircle className="text-bad" size={18} />
              : done ? (d.status === 'failed' ? <XCircle className="text-bad" size={18} /> : <CheckCircle2 className="text-ok" size={18} />)
                : <Loader2 className="animate-spin text-brand-600" size={18} />}
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium">{x.file.name}</div>
            {d && !done && <Stepper status={d.status} started={x.started} />}
            <div className="text-xs text-slate-500">
              {x.error ? <span className="text-bad">{x.error}{x.dupId && <> — <Link className="underline" to={`/documents/${x.dupId}`}>{t('open existing')}</Link></>}</span>
                : !d ? t('Uploading…')
                  : !done ? t('usually 10–30 seconds per page; digital PDFs about a second')
                    : d.status === 'failed' ? t('Could not process this file')
                      : `${d.district || t('Unknown district')} · ${t('processed in')} ${((d.processing_ms || 0) / 1000).toFixed(1)} s`}
            </div>
            {done && worstQuality(d.pages)?.verdict === 'poor' &&
              <div className="mt-1 flex items-start gap-1.5 text-xs font-medium text-bad">
                <Camera size={14} className="mt-0.5 shrink-0" />
                <span>{t('Image too poor to read reliably — please retake')}: {worstQuality(d.pages).advice.join('; ')}</span>
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
