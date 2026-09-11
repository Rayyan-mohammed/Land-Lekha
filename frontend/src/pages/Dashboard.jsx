import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Link } from 'react-router-dom'
import { AlertTriangle, ArrowRight, Brain, CheckCircle2, Clock, FileStack, Gauge, Hourglass, ScanText, Target } from 'lucide-react'
import { api } from '../api'
import { ErrorNote, locale, PageHeader, SkeletonCards, Stat } from '../components/ui'
import { useAuth } from '../auth'
import { FIELD_MAP, STATUS } from '../constants'
import { useT } from '../i18n'
import { explainIssue } from '../reasons'

const pct = (v, d = 1) => (v == null ? '—' : `${(v * 100).toFixed(d)}%`)
const STATUS_COLORS = { auto_accepted: '#15803d', verified: '#1f6f69', needs_review: '#d97706', rejected: '#b91c1c', failed: '#7f1d1d', processing: '#0284c7', queued: '#94a3b8' }

function Section({ title, subtitle, children, className = '' }) {
  const { t } = useT()
  title = t(title)
  subtitle = subtitle && t(subtitle)
  return <div className={`card min-w-0 p-4 ${className}`}>
    <div className="mb-3"><div className="font-medium text-slate-900">{title}</div>{subtitle && <div className="text-xs text-slate-500">{subtitle}</div>}</div>
    {children}
  </div>
}

function greeting(t) {
  const h = new Date().getHours()
  return t(h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening')
}

export default function Dashboard() {
  const { t: tr, lang } = useT()
  const { user } = useAuth()
  const [s, setS] = useState(null)
  const [error, setError] = useState(null)
  useEffect(() => {
    const load = () => api.stats().then(setS).catch(setError)
    load()
    const t = setInterval(load, 10000)
    return () => clearInterval(t)
  }, [])
  if (error) return <ErrorNote error={error} />
  if (!s) return <div className="space-y-4"><PageHeader title={tr('Digitization dashboard')} subtitle={tr('Loading live figures…')} /><SkeletonCards n={8} /></div>

  const t = s.totals
  const bench = s.accuracy.benchmark
  const statusData = Object.entries(t.by_status).map(([k, v]) => ({ name: tr(STATUS[k]?.label || k), key: k, value: v }))
  const hist = s.confidence.histogram.map((n, i) => ({ bucket: `${i * 10}–${i * 10 + 10}%`, documents: n }))
  const perField = Object.entries(s.accuracy.per_field).map(([k, v]) => ({ field: FIELD_MAP[k]?.[lang === 'hi' ? 'hi' : 'en'] || k, accuracy: Math.round(v.accuracy * 100), n: v.confirmed + v.corrected + v.rejected }))
    .sort((a, b) => a.accuracy - b.accuracy)

  return <div className="space-y-4">
    <PageHeader title={`${greeting(tr)}, ${user?.full_name?.split(' ')[0] || ''}`}
      subtitle={`${tr('Digitization dashboard')} · ${new Date().toLocaleDateString(locale(), { weekday: 'long', day: 'numeric', month: 'long' })} · ${tr('refreshes every 10 seconds')}`} />
    {(t.pending_verification > 0 || t.failed > 0) && <div className="flex flex-wrap gap-3">
      {t.pending_verification > 0 && <Link to="/review" className="card group flex flex-1 items-center gap-3 border-amber-200 bg-amber-50 p-4 transition-colors duration-200 hover:border-amber-300">
        <Hourglass size={20} className="text-warn" />
        <div className="flex-1"><div className="font-medium text-slate-900">{t.pending_verification} {tr(t.pending_verification === 1 ? 'document waits for a verifier' : 'documents wait for a verifier')}</div>
          <div className="text-xs text-slate-600">{tr('Lowest confidence first; usually one or two fields each')}</div></div>
        <span className="inline-flex items-center gap-1 text-sm font-medium text-brand-700">{tr('Start reviewing')} <ArrowRight size={15} className="transition-transform duration-200 group-hover:translate-x-0.5" /></span>
      </Link>}
      {t.failed > 0 && <Link to="/documents?status=failed" className="card group flex flex-1 items-center gap-3 border-red-200 bg-red-50 p-4 transition-colors duration-200 hover:border-red-300">
        <AlertTriangle size={20} className="text-bad" />
        <div className="flex-1"><div className="font-medium text-slate-900">{t.failed} {tr(t.failed === 1 ? 'file could not be processed' : 'files could not be processed')}</div>
          <div className="text-xs text-slate-600">{tr('Usually unreadable or corrupt uploads')}</div></div>
        <ArrowRight size={15} className="text-bad" />
      </Link>}
    </div>}
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Stat icon={FileStack} label={tr('Documents processed')} value={t.processed} sub={`${t.documents} ${tr('received')} · ${t.land_records} ${tr('records created')}`} />
      <Stat icon={CheckCircle2} tone="ok" label={tr('Auto-accepted')} value={pct(t.auto_accept_rate, 0)} sub={tr('no human needed')} />
      <Stat icon={Hourglass} tone="warn" label={tr('Pending verification')} value={t.pending_verification} sub={`${t.failed} ${tr('failed')}`} />
      <Stat icon={Clock} tone="slate" label={tr('Avg. processing')} value={s.processing.avg_seconds ? `${s.processing.avg_seconds} s` : '—'} sub={tr('upload → structured record')} />
      <Stat icon={Target} tone="ok" label={tr('Field accuracy (reviewed)')} value={pct(s.accuracy.field_accuracy)} sub={`${s.accuracy.reviewed_fields} ${tr('fields checked by verifiers')}`} />
      <Stat icon={ScanText} label={tr('Benchmark CER')} value={bench ? pct(bench.cer_median) : '—'} sub={bench ? `${tr('median')}, ${bench.documents} ${tr('held-out test docs')}` : 'run eval/evaluate.py'} />
      <Stat icon={Gauge} label={tr('Benchmark field accuracy')} value={bench ? pct(bench.field_accuracy) : '—'}
        sub={bench?.straight_through_accuracy != null ? `${pct(bench.straight_through_accuracy)} ${tr('correct when auto-accepted')}` : ''} />
      <Stat icon={Brain} tone="slate" label={tr('Learned from verifiers')} value={s.learning.corrections} sub={`${s.learning.learned_patterns} ${tr('correction patterns active')}`} />
    </div>

    <div className="grid gap-4 lg:grid-cols-3">
      <Section title="Validation status" subtitle="Where every document stands" className="lg:col-span-1">
        <div className="space-y-2">
          {statusData.sort((a, b) => b.value - a.value).map((d) => <div key={d.key}>
            <div className="flex justify-between text-sm"><span>{d.name}</span><span className="tabular-nums font-medium">{d.value}</span></div>
            <div className="h-2 rounded-full bg-slate-100"><div className="h-2 rounded-full" style={{ width: `${(d.value / Math.max(1, t.documents)) * 100}%`, background: STATUS_COLORS[d.key] }} /></div>
          </div>)}
          {statusData.length === 0 && <div className="text-sm text-slate-500">{tr('No documents yet.')}</div>}
        </div>
      </Section>
      <Section title="Uploads, last 14 days" className="lg:col-span-2">
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={s.trend} margin={{ left: -20, right: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="day" tickFormatter={(d) => d.slice(5)} fontSize={11} />
            <YAxis allowDecimals={false} fontSize={11} />
            <Tooltip /><Legend />
            <Line type="monotone" dataKey="uploaded" stroke="#1f6f69" strokeWidth={2} dot={false} name={tr('Uploaded')} />
            <Line type="monotone" dataKey="auto_accepted" stroke="#15803d" strokeWidth={2} strokeDasharray="4 3" dot={false} name={tr('Auto-accepted')} />
          </LineChart>
        </ResponsiveContainer>
      </Section>
    </div>

    <div className="grid gap-4 lg:grid-cols-2">
      <Section title="State-wise and district-wise progress" subtitle="Digitized = auto-accepted + verified">
        <div className="table-wrap"><table className="data">
          <thead><tr><th>{tr('State / District')}</th><th className="text-right">{tr('Received')}</th><th className="text-right">{tr('Pending')}</th><th>{tr('Digitized')}</th></tr></thead>
          <tbody>{s.geography.flatMap((g) => [
            <tr key={g.state}><td className="font-medium">{g.state}</td><td className="text-right tabular-nums">{g.total}</td><td /><td /></tr>,
            ...g.districts.map((d) => {
              const done = (d.auto_accepted || 0) + (d.verified || 0)
              return <tr key={g.state + d.district}>
                <td className="pl-6 text-slate-600">{d.district}</td>
                <td className="text-right tabular-nums">{d.total}</td>
                <td className="text-right tabular-nums text-warn">{d.needs_review || 0}</td>
                <td><div className="flex items-center gap-2"><div className="h-1.5 w-20 rounded-full bg-slate-100"><div className="h-1.5 rounded-full bg-brand-600" style={{ width: `${(done / d.total) * 100}%` }} /></div>
                  <span className="text-xs tabular-nums">{Math.round((done / d.total) * 100)}%</span></div></td>
              </tr>
            }),
          ])}</tbody>
        </table></div>
        {s.geography.length === 0 && <div className="text-sm text-slate-500">{tr('No data yet.')}</div>}
      </Section>
      <Section title="Confidence distribution" subtitle={`${tr('Documents by overall confidence')} · ${tr('auto-accept threshold')} ${pct(s.confidence.threshold, 0)} ${tr('per field')}`}>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={hist} margin={{ left: -20, right: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="bucket" fontSize={10} interval={1} />
            <YAxis allowDecimals={false} fontSize={11} />
            <Tooltip />
            <Bar dataKey="documents" name={tr('documents')} fill="#2a8a82" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Section>
    </div>

    <div className="grid gap-4 lg:grid-cols-2">
      <Section title="Accuracy by field" subtitle="Share of reviewed fields the verifier left unchanged">
        {perField.length === 0 ? <div className="text-sm text-slate-500">{tr('No reviewed fields yet.')}</div> :
          <ResponsiveContainer width="100%" height={Math.max(160, perField.length * 26)}>
            <BarChart data={perField} layout="vertical" margin={{ left: 40, right: 16 }}>
              <XAxis type="number" domain={[0, 100]} fontSize={11} unit="%" />
              <YAxis type="category" dataKey="field" fontSize={11} width={110} />
              <Tooltip formatter={(v, _, p) => [`${v}% (${p.payload.n} ${tr('reviewed')})`, tr('accuracy')]} />
              <Bar dataKey="accuracy" fill="#1f6f69" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>}
      </Section>
      <Section title="Error statistics" subtitle="Most common validation issues and review reasons">
        <div className="grid gap-4 sm:grid-cols-2">
          <div><div className="label">{tr('Field issues')}</div>
            {s.errors.issues.map(([k, n]) => <div key={k} className="flex justify-between gap-2 border-b border-slate-100 py-1 text-sm"><span className="truncate" title={k}>{explainIssue(k, lang)}</span><span className="tabular-nums text-slate-500">{n}</span></div>)}
            {s.errors.issues.length === 0 && <div className="text-sm text-slate-500">{tr('None')}</div>}</div>
          <div><div className="label">{tr('Why sent to review')}</div>
            {s.errors.review_reasons.map(([k, n]) => <div key={k} className="flex justify-between gap-2 border-b border-slate-100 py-1 text-sm"><span className="truncate" title={k}>{explainIssue(k, lang)}</span><span className="tabular-nums text-slate-500">{n}</span></div>)}
            {s.errors.review_reasons.length === 0 && <div className="text-sm text-slate-500">{tr('None')}</div>}</div>
        </div>
        {Object.keys(s.learning.adapted_thresholds).length > 0 && <div className="mt-3 text-xs text-slate-600">
          <span className="label">{tr('Adapted thresholds (fields often corrected)')}</span>
          {Object.entries(s.learning.adapted_thresholds).map(([k, v]) => <span key={k} className="mr-3">{FIELD_MAP[k]?.[lang === 'hi' ? 'hi' : 'en'] || k}: {pct(v, 0)}</span>)}
        </div>}
      </Section>
    </div>
  </div>
}
