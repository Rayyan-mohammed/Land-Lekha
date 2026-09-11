import { ClipboardCheck, FileUp, Keyboard, Printer, ShieldCheck, Upload } from 'lucide-react'
import { PageHeader } from '../components/ui'
import { useT } from '../i18n'

const GUIDES = [
  [Upload, 'Operators', [
    'Upload scans, PDFs or phone photos from the Upload page. Several files at once is fine.',
    'Each file shows its progress. Digital PDFs from the land portal finish in about a second.',
    'If a photo is too blurred, you are told straight away. Retake it before the owner leaves the counter.',
  ]],
  [ClipboardCheck, 'Verifiers', [
    'The Review queue lists documents with at least one uncertain field, lowest confidence first.',
    'You only check what is flagged. The scan is on the left, with a box on every field; click a box to jump to it.',
    'Confirm, correct or reject each flagged field, then approve. Corrections are remembered and applied to future documents.',
  ]],
  [ShieldCheck, 'Administrators', [
    'The Dashboard shows progress by state and district, accuracy, and what is waiting.',
    'Users & roles: create accounts, change roles, reset passwords. Everything is recorded in the audit trail.',
  ]],
  [Printer, 'Verified extracts', [
    'From Records & GIS, open a record and print its extract. The QR code on it lets anyone check it is genuine and current.',
  ]],
]

const COLOURS = [
  ['border-ok bg-emerald-50', 'Green', 'confident: passed every check, above the auto-accept threshold'],
  ['border-warn bg-amber-50', 'Amber', 'please check: readable but not certain'],
  ['border-bad bg-red-50', 'Red', 'probably wrong or failed a rule (format, master data)'],
]

const KEYS = [['↑ ↓', 'move between fields'], ['N', 'next flagged field'], ['Enter', 'confirm the field'], ['X', 'reject the field'],
  ['E', 'edit the value'], ['Ctrl + Enter', 'approve the record'], ['Esc', 'leave the text box']]

const FAQ = [
  ['Why was my photo marked "poor"?', 'The text could not be read reliably, usually blur, shadow or a page that is too small in the frame. A clearer photo or the portal PDF fixes it; guessing would put wrong data into the record.'],
  ['What does the percentage mean?', 'How likely the value is to be correct, learned from checked examples. Fields below the threshold always go to a person.'],
  ['The village was not found. What now?', 'Check the spelling against the official village list. If the village is genuinely missing, tell the administrator so the master list can be updated.'],
  ['Can an approval be undone?', 'Not from the screen. Every approval is kept in the audit trail with who and when; an administrator can re-issue a corrected record.'],
]

export default function Help() {
  const { t } = useT()
  return <div className="space-y-4">
    <PageHeader title={t('Help')} subtitle="How LandLekha works, in two minutes" />
    <div className="grid gap-4 md:grid-cols-2">
      {GUIDES.map(([Icon, title, points]) => <section key={title} className="card p-4">
        <h2 className="flex items-center gap-2 font-medium text-slate-900"><Icon size={17} className="text-brand-600" /> {title}</h2>
        <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm text-slate-700">{points.map((p) => <li key={p}>{p}</li>)}</ul>
      </section>)}
    </div>
    <div className="grid gap-4 md:grid-cols-2">
      <section className="card p-4">
        <h2 className="font-medium text-slate-900">What the colours mean</h2>
        <ul className="mt-2 space-y-2 text-sm">{COLOURS.map(([cls, name, text]) => <li key={name} className="flex items-center gap-2.5">
          <span className={`h-4 w-4 shrink-0 rounded-sm border-2 ${cls}`} /><span><span className="font-medium">{name}</span>: {text}</span></li>)}</ul>
      </section>
      <section className="card p-4">
        <h2 className="flex items-center gap-2 font-medium text-slate-900"><Keyboard size={17} className="text-brand-600" /> Review shortcuts</h2>
        <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-sm">
          {KEYS.map(([k, what]) => <div key={k} className="contents"><dt><kbd className="kbd">{k}</kbd></dt><dd className="text-slate-700">{what}</dd></div>)}
        </dl>
      </section>
    </div>
    <section className="card p-4">
      <h2 className="flex items-center gap-2 font-medium text-slate-900"><FileUp size={17} className="text-brand-600" /> Common questions</h2>
      <div className="mt-2 divide-y divide-slate-100">{FAQ.map(([q, a]) => <details key={q} className="group py-2.5">
        <summary className="text-sm font-medium text-slate-800 marker:text-brand-600">{q}</summary>
        <p className="mt-1.5 text-sm text-slate-600">{a}</p>
      </details>)}</div>
    </section>
  </div>
}
