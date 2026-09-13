import { useEffect, useState } from 'react'
import { CheckCircle2, ClipboardList, FileUp, XCircle } from 'lucide-react'
import { api } from '../api'
import { ErrorNote, fmtDate, PageHeader, Spinner } from '../components/ui'
import { FIELDS, LAND_CLASSES } from '../constants'
import { useToast } from '../components/toast'
import { useT } from '../i18n'

const UNITS = ['hectare', 'acre', 'bigha', 'sqm']
const ACCEPT = '.png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp,.pdf'

function fieldsFromForm(form) {
  const out = {}
  for (const f of FIELDS) {
    if (f.name === 'plot_area') {
      if (form.plot_area_value) out.plot_area = { value: Number(form.plot_area_value), unit: form.plot_area_unit || 'hectare' }
      continue
    }
    const v = (form[f.name] || '').trim()
    if (v) out[f.name] = v
  }
  return out
}

export default function RealSamples() {
  const { t, lang } = useT()
  const fieldLabel = (f) => f[lang === 'hi' ? 'hi' : 'en']
  const toast = useToast()
  const [file, setFile] = useState(null)
  const [form, setForm] = useState({ plot_area_unit: 'hectare' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [history, setHistory] = useState(null)

  const loadHistory = () => api.realSamples().then((v) => { setHistory(v); setError(null) }).catch(setError)
  useEffect(() => { loadHistory() }, [])

  const submit = async (e) => {
    e.preventDefault()
    const fields = fieldsFromForm(form)
    if (!file || Object.keys(fields).length === 0) return
    setBusy(true); setError(null); setResult(null)
    try {
      const r = await api.addRealSample(file, fields)
      setResult(r)
      toast(t('Measured'), { body: `${t('Field accuracy')}: ${r.field_accuracy != null ? Math.round(r.field_accuracy * 100) + '%' : '—'}` })
      loadHistory()
    } catch (err) { setError(err) } finally { setBusy(false) }
  }

  return <div>
    <PageHeader title={t('Real document check')}
      subtitle={t('Upload a real land record and the correct field values you read off it, and see the pipeline’s accuracy on it immediately. Saved into data/real/ so it also counts toward the full benchmark.')} />
    <ErrorNote error={error} />
    <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
      <form onSubmit={submit} className="card space-y-4 p-4">
        <div>
          <label className="label" htmlFor="rs-file">{t('Document')}</label>
          <input id="rs-file" type="file" accept={ACCEPT} className="input" onChange={(e) => setFile(e.target.files?.[0] || null)} />
        </div>
        <div className="text-xs text-slate-500">{t('Fill in only the fields actually on the page - leave the rest blank.')}</div>
        <div className="grid gap-3 sm:grid-cols-2">
          {FIELDS.map((f) => f.name === 'plot_area'
            ? <div key="plot_area" className="sm:col-span-2">
                <label className="label" htmlFor="rs-area">{fieldLabel(f)}</label>
                <div className="flex gap-2">
                  <input id="rs-area" type="number" step="any" className="input"
                    value={form.plot_area_value || ''} onChange={(e) => setForm({ ...form, plot_area_value: e.target.value })} />
                  <select className="input w-auto" value={form.plot_area_unit} onChange={(e) => setForm({ ...form, plot_area_unit: e.target.value })}>
                    {UNITS.map((u) => <option key={u} value={u}>{u}</option>)}
                  </select>
                </div>
              </div>
            : f.name === 'land_classification'
            ? <div key={f.name}>
                <label className="label" htmlFor="rs-lc">{fieldLabel(f)}</label>
                <select id="rs-lc" className="input" value={form.land_classification || ''} onChange={(e) => setForm({ ...form, land_classification: e.target.value })}>
                  <option value="">{t('not on this page')}</option>
                  {Object.keys(LAND_CLASSES).map((k) => <option key={k} value={k}>{LAND_CLASSES[k]}</option>)}
                </select>
              </div>
            : <div key={f.name}>
                <label className="label" htmlFor={`rs-${f.name}`}>{fieldLabel(f)}</label>
                <input id={`rs-${f.name}`} className="input" value={form[f.name] || ''} onChange={(e) => setForm({ ...form, [f.name]: e.target.value })} />
              </div>)}
        </div>
        <button className="btn-primary w-full" disabled={busy || !file}>
          {busy ? <><Spinner className="h-4 w-4" /> {t('Reading and comparing…')}</> : <><FileUp size={15} /> {t('Check accuracy')}</>}
        </button>
      </form>

      <div className="space-y-4">
        {result && <div className="card space-y-3 p-4">
          <div className="flex items-center justify-between">
            <div className="font-medium text-slate-900">{t('Result')}</div>
            <div className="text-lg font-semibold tabular-nums text-slate-900">
              {result.field_accuracy != null ? `${Math.round(result.field_accuracy * 100)}%` : '—'}
            </div>
          </div>
          <div className="text-xs text-slate-500">{result.document_type} · {t('route')}: {result.route} · {t('overall confidence')} {result.overall_confidence != null ? Math.round(result.overall_confidence * 100) + '%' : '—'}</div>
          <ul className="divide-y divide-slate-100 text-sm">
            {result.fields.map((c) => <li key={c.field} className="flex items-start justify-between gap-2 py-1.5">
              <div className="min-w-0">
                <div className="font-medium">{(() => { const f = FIELDS.find((f) => f.name === c.field); return f ? fieldLabel(f) : c.field })()}</div>
                <div className="truncate text-xs text-slate-500">{t('correct')}: {typeof c.ground_truth === 'object' ? `${c.ground_truth.value} ${c.ground_truth.unit}` : String(c.ground_truth)}</div>
                <div className="truncate text-xs text-slate-500">{t('extracted')}: {c.extracted ?? t('not found')}</div>
              </div>
              {c.correct ? <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-ok" /> : <XCircle size={16} className="mt-0.5 shrink-0 text-bad" />}
            </li>)}
          </ul>
        </div>}

        <div className="card p-4">
          <div className="mb-2 flex items-center gap-2 font-medium text-slate-900"><ClipboardList size={16} /> {t('Samples measured so far')}</div>
          {!history ? <div className="text-sm text-slate-500">{t('Loading…')}</div>
            : history.length === 0 ? <div className="text-sm text-slate-500">{t('None yet.')}</div>
            : <ul className="space-y-1.5 text-sm">
                {history.map((s) => <li key={s.sample_id} className="flex items-center justify-between gap-2">
                  <span className="truncate text-slate-600">{s.sample_id}</span>
                  <span className="shrink-0 text-xs text-slate-400">{fmtDate(s.added)}</span>
                </li>)}
              </ul>}
        </div>
      </div>
    </div>
  </div>
}
