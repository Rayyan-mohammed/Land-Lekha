import { useState } from 'react'
import { AlertTriangle, CheckCircle2, Database, Loader2 } from 'lucide-react'
import { api } from '../api'
import { useT } from '../i18n'
import { FIELDS } from '../constants'

// What we read off the page, against what the state register holds. The register is
// simulated - there is no state API to call - and the card says so, because a match here
// means the two records agree, not that the document is genuine.
export default function RegisterCheck({ docId }) {
  const { t, lang } = useT()
  const [state, setState] = useState(null)
  const [busy, setBusy] = useState(false)

  const run = async () => {
    setBusy(true)
    try { setState(await api.registerCheck(docId)) } finally { setBusy(false) }
  }

  const label = (name) => FIELDS.find((f) => f.name === name)?.[lang === 'hi' ? 'hi' : 'en'] || name
  const rows = state ? Object.entries(state.fields).filter(([, v]) => v.status !== 'not_held') : []

  return <div className="card mb-4 p-3">
    <div className="flex flex-wrap items-center gap-2">
      <Database size={16} className="text-brand-600" />
      <span className="font-medium text-slate-900">{t('Check against the state register')}</span>
      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">{t('simulated')}</span>
      <button className="btn-outline ml-auto py-1 text-xs" onClick={run} disabled={busy}>
        {busy ? <Loader2 size={14} className="animate-spin" /> : null} {t('Check')}
      </button>
    </div>

    {state && !state.found &&
      <div className="mt-2 text-sm text-slate-600">{t('No matching parcel in the register')} · {state.register_size} {t('entries')}</div>}

    {state && state.found && <>
      <div className={`mt-2 flex items-center gap-2 text-sm ${state.differ ? 'text-warn' : 'text-ok'}`}>
        {state.differ ? <AlertTriangle size={15} /> : <CheckCircle2 size={15} />}
        {state.differ
          ? `${state.differ} ${t(state.differ === 1 ? 'field differs from the register' : 'fields differ from the register')}`
          : t('Every field matches the register')}
      </div>
      <div className="table-wrap mt-2"><table className="data">
        <thead><tr><th>{t('Field')}</th><th>{t('On this document')}</th><th>{t('In the register')}</th></tr></thead>
        <tbody>{rows.map(([name, v]) => <tr key={name} className={v.status === 'differ' ? 'bg-amber-50' : ''}>
          <td className="text-slate-600">{label(name)}</td>
          <td className="font-medium">{v.ours}</td>
          <td className={v.status === 'differ' ? 'font-medium text-warn' : 'text-slate-600'}>{v.register}</td>
        </tr>)}</tbody>
      </table></div>
      <div className="mt-2 text-[11px] text-slate-500">
        {t('A match means the two records agree. It is not evidence that the document is genuine.')}
      </div>
    </>}
  </div>
}
