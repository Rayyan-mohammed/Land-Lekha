import { CheckCircle2, Landmark, ShieldAlert, XCircle } from 'lucide-react'
import { docTypeLabel } from '../constants'
import { useT } from '../i18n'

const SCRIPT_HI = { Latin: 'रोमन', Devanagari: 'देवनागरी', Telugu: 'तेलुगु', Tamil: 'तमिल', Kannada: 'कन्नड़', Bengali: 'बांग्ला',
  Gujarati: 'गुजराती', Gurmukhi: 'गुरमुखी', Malayalam: 'मलयालम', Oriya: 'ओड़िया', Arabic: 'अरबी / उर्दू' }
const KIND_HI = { 'parcel identifier': 'खसरा / खाता / सर्वे', extent: 'क्षेत्रफल', tenure: 'स्वामित्व', 'revenue office': 'राजस्व कार्यालय',
  'land use': 'भूमि उपयोग', boundaries: 'चौहद्दी', transaction: 'लेन-देन' }
const pct = (v) => `${Math.round((v || 0) * 100)}%`

// Why the classifier said no, in the reader's language
function explainVerdict(r, lang) {
  if (lang !== 'hi' || !r) return r
  if (r.startsWith('no land-record evidence')) return 'पन्ने पर भू-अभिलेख का कोई प्रमाण नहीं'
  if (r.startsWith('only one kind')) return 'भू-अभिलेख का केवल एक ही तरह का प्रमाण'
  if (r.startsWith('reads like')) return 'यह भू-अभिलेख नहीं, किसी और तरह का दस्तावेज़ लगता है'
  if (r.startsWith('land evidence is weak')) return 'भू-अभिलेख का प्रमाण कमज़ोर है'
  return r
}

/** What the land-document classifier decided about this document, before any field was read.
 *  Three separate things, kept separate on purpose: is it a land record, what kind, and whether
 *  it carries government wording - which is reported, never treated as proof of authenticity. */
export function ClassificationCard({ verdict, layoutType }) {
  const { t, lang } = useT()
  if (!verdict) return null
  const hi = lang === 'hi'
  if (verdict.undetermined) {
    return <div className="mb-4 rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-800">
      <div className="flex items-center gap-2 font-medium"><ShieldAlert size={16} /> {t('Could not tell what this page is')}</div>
      <div className="mt-1 text-[13px] text-slate-600">{t('Too little was read from it to say whether it is a land record. The quality check has the details.')}</div>
    </div>
  }
  if (verdict.is_land_document === false) {
    return <div className="mb-4 rounded-xl border-2 border-red-300 bg-red-50 p-4 text-sm text-red-900" role="alert">
      <div className="flex items-center gap-2 text-base font-semibold"><XCircle size={20} /> {t('NOT A LAND DOCUMENT')}</div>
      <div className="mt-1">{t('Confidence')}: <span className="font-medium tabular-nums">{pct(verdict.confidence)}</span>
        {' · '}{explainVerdict(verdict.reason, lang)}</div>
      <div className="mt-2 text-[13px] text-red-800">{t('No land-record fields were extracted from this page, so none can be shown. If this really is a land record, a verifier can look at the page image.')}</div>
    </div>
  }
  const type = verdict.document_type && verdict.document_type !== 'unknown' ? verdict.document_type : null
  const kinds = Object.keys(verdict.evidence || {})
  return <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950">
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
      <span className="flex items-center gap-2 text-base font-semibold"><CheckCircle2 size={20} /> {t('LAND DOCUMENT')}</span>
      <span>{t('Confidence')}: <span className="font-medium tabular-nums">{pct(verdict.confidence)}</span></span>
    </div>
    <dl className="mt-2 grid gap-x-6 gap-y-1 text-[13px] sm:grid-cols-2">
      <div><dt className="inline text-emerald-800">{t('Document type')}: </dt>
        <dd className="inline font-medium">
          {type
            ? <>{docTypeLabel(type, lang)}
                {verdict.type_family && verdict.type_family !== type && <span className="font-normal text-emerald-800"> ({docTypeLabel(verdict.type_family, lang)})</span>}
                <span className="font-normal text-emerald-800"> · {pct(verdict.document_type_confidence)}</span></>
            : <>{t('unknown')} <span className="font-normal text-emerald-800">— {t('manual review recommended')}</span>
                {layoutType && layoutType !== 'unknown' && <span className="font-normal text-emerald-800"> · {t('layout reads as')} {docTypeLabel(layoutType, lang)}</span>}</>}
        </dd></div>
      <div><dt className="inline text-emerald-800">{t('Scripts on the page')}: </dt>
        <dd className="inline font-medium">{(verdict.scripts || []).map((sc) => (hi ? (SCRIPT_HI[sc] || sc) : sc)).join(' + ') || '—'}</dd></div>
      <div className="sm:col-span-2"><dt className="inline text-emerald-800">{t('Evidence')}: </dt>
        <dd className="inline">
          {kinds.map((k) => <span key={k} className="mr-1 inline-block rounded-full bg-white/70 px-2 py-0.5 text-[12px] text-emerald-900" title={(verdict.evidence[k] || []).join(', ')}>{hi ? (KIND_HI[k] || k) : k}</span>)}
          <span className="text-emerald-800">({kinds.length} {t('kinds of land evidence')})</span>
        </dd></div>
      {verdict.government_indicators?.length > 0 && <div className="flex items-start gap-1.5 sm:col-span-2">
        <Landmark size={14} className="mt-0.5 shrink-0 text-emerald-800" />
        <span><span className="font-medium">{t('Government / revenue indicators detected')}</span>
          <span className="text-emerald-800"> — {t('this is not proof of authenticity; authenticity cannot be verified from the image alone')}</span></span>
      </div>}
    </dl>
  </div>
}
