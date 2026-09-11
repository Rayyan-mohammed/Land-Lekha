import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import QRCode from 'qrcode'
import { Printer, ShieldCheck } from 'lucide-react'
import { api } from '../api'
import { ErrorNote, Spinner } from '../components/ui'
import { LAND_CLASSES } from '../constants'

function Row({ label, hi, children }) {
  return <tr className="border-b border-slate-200">
    <th className="w-56 py-2 pr-4 text-left align-top text-xs font-medium text-slate-500">{label}<div className="font-normal">{hi}</div></th>
    <td className="py-2 text-sm text-slate-900">{children || '—'}</td>
  </tr>
}

const cls = (k) => LAND_CLASSES[k] || k || '—'

// A printable, verifiable extract of one digitized land record.
export default function Extract() {
  const { id } = useParams()
  const [ex, setEx] = useState(null)
  const [qr, setQr] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.extract(id).then(async (e) => {
      setEx(e)
      setQr(await QRCode.toDataURL(window.location.origin + e.verify_path, { margin: 1, width: 180 }))
    }).catch(setError)
  }, [id])

  if (error) return <ErrorNote error={error} />
  if (!ex) return <div className="flex justify-center p-16"><Spinner /></div>
  const r = ex.record
  const owners = r.owners?.length ? r.owners : [{ owner_name: r.owner_name, father_name: r.father_name }]
  const parcels = r.parcels?.length ? r.parcels
    : [{ khasra_number: r.khasra_number, plot_area: r.plot_area, land_classification: r.land_classification }]

  return <div>
    <div className="no-print mb-4 flex items-center justify-between">
      <div className="text-sm text-slate-500">Check the details, then print or save as PDF.</div>
      <button className="btn-primary" onClick={() => window.print()}><Printer size={16} /> Print extract</button>
    </div>
    <div className="extract-sheet card mx-auto max-w-3xl p-8">
      <div className="flex items-start justify-between gap-6 border-b-2 border-slate-800 pb-4">
        <div>
          <div className="text-xs uppercase tracking-widest text-slate-500">Digitized land record · भूमि अभिलेख</div>
          <h1 className="mt-1 text-2xl font-semibold text-slate-900">Verified record extract</h1>
          <div className="text-sm text-slate-600">Record #{r.record_id} · {r.village}, {r.tehsil}, {r.district}, {r.state}</div>
        </div>
        {qr && <img src={qr} alt="QR code to verify this extract" className="h-32 w-32" />}
      </div>

      <table className="mt-4 w-full">
        <tbody>
          <Row label="State / District" hi="राज्य / जिला">{r.state} / {r.district}</Row>
          <Row label="Tehsil / Village" hi="तहसील / ग्राम">{r.tehsil} / {r.village}</Row>
          <Row label="Khata No." hi="खाता संख्या">{r.khata_number}</Row>
          <Row label={owners.length > 1 ? `Co-owners (${owners.length})` : 'Landowner'} hi="खातेदार">
            <ol className="space-y-0.5">{owners.map((o, i) => <li key={i}>{owners.length > 1 && `${i + 1}. `}<span className="font-medium">{o.owner_name}</span>
              {o.father_name && <span className="text-slate-500"> · s/o, d/o, w/o {o.father_name}</span>}</li>)}</ol>
          </Row>
          <Row label="Parcels" hi="खसरा / क्षेत्रफल / भूमि का प्रकार">
            <table className="w-full text-sm"><tbody>{parcels.map((p, i) => <tr key={i}>
              <td className="pr-4 tabular-nums">{p.khasra_number}</td><td className="pr-4 tabular-nums">{p.plot_area}</td><td>{cls(p.land_classification)}</td>
            </tr>)}</tbody></table>
            {ex.area_hectares != null && parcels.length === 1 && <div className="text-xs text-slate-500">{ex.area_hectares} hectare</div>}
          </Row>
          {r.survey_number && <Row label="Survey No." hi="सर्वे संख्या">{r.survey_number}</Row>}
          {r.mutation_number && <Row label="Mutation" hi="नामांतरण">No. {r.mutation_number}{r.mutation_date && `, dated ${r.mutation_date}`}</Row>}
          {r.registration_number && <Row label="Registration" hi="पंजीकरण">No. {r.registration_number}{r.registration_date && `, dated ${r.registration_date}`}</Row>}
        </tbody>
      </table>

      <div className="mt-6 grid gap-4 rounded-lg bg-slate-50 p-4 text-xs text-slate-600 sm:grid-cols-2">
        <div>
          <div className="flex items-center gap-1 font-medium text-slate-800"><ShieldCheck size={14} /> How this was verified</div>
          <div>{ex.verification === 'human' ? 'Checked and approved by a verifier' : 'Accepted automatically: every field passed validation'} ·
            source document #{ex.source_document_id}{ex.lrms_ref && ` · LRMS ${ex.lrms_ref}`}</div>
          <div>Issued {new Date(ex.issued_at).toLocaleString()} by {ex.issued_by}</div>
        </div>
        <div>
          <div className="font-medium text-slate-800">Record fingerprint</div>
          <div className="font-mono text-sm tracking-wider text-slate-900">{ex.fingerprint_short}</div>
          <div>Scan the QR code to check this extract against the live record. If anything in the record has changed, the check fails.</div>
        </div>
      </div>
    </div>
  </div>
}
