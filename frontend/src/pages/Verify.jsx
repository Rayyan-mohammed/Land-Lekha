import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { CheckCircle2, QrCode, Volume2, VolumeX, XCircle } from 'lucide-react'
import { api } from '../api'
import { Logo } from '../components/Layout'
import { Spinner } from '../components/ui'

// Kiosk mode: a tehsil-office terminal (or anyone without their own smartphone camera
// shortcut) can scan a printed extract's QR right here, no app or QR-scanner app needed.
// Uses the browser-native BarcodeDetector (Chrome/Edge/Android) - no library, no server
// round-trip for the scan itself. Where it is not available (notably Safari/iOS), a citizen's
// own phone camera app already opens the same QR directly, so this is a bonus, not the only path.
export function VerifyScan() {
  const nav = useNavigate()
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState(null)
  const supported = typeof window !== 'undefined' && 'BarcodeDetector' in window

  useEffect(() => { document.title = 'Scan an extract · नकल स्कैन करें · LandLekha' }, [])
  useEffect(() => () => streamRef.current?.getTracks().forEach((t) => t.stop()), [])

  const start = async () => {
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
      streamRef.current = stream
      videoRef.current.srcObject = stream
      await videoRef.current.play()
      setScanning(true)
      const detector = new window.BarcodeDetector({ formats: ['qr_code'] })
      const loop = async () => {
        if (!streamRef.current) return
        try {
          const codes = await detector.detect(videoRef.current)
          if (codes.length) {
            const url = new URL(codes[0].rawValue, window.location.href)
            if (url.origin === window.location.origin && /^\/verify\/[^/]+/.test(url.pathname)) {
              streamRef.current.getTracks().forEach((t) => t.stop())
              streamRef.current = null
              nav(url.pathname + url.search)
              return
            }
          }
        } catch { /* a frame that fails to decode just tries again */ }
        requestAnimationFrame(loop)
      }
      requestAnimationFrame(loop)
    } catch {
      setError('camera')
    }
  }

  return <main className="min-h-full bg-slate-50 p-6">
    <div className="mx-auto max-w-lg">
      <div className="mb-6"><Logo /></div>
      <div className="card p-6 text-center">
        <h1 className="text-lg font-semibold text-slate-900">Scan an extract · नकल स्कैन करें</h1>
        <p className="mt-1 text-sm text-slate-600">Point the camera at the QR code printed on a LandLekha extract.
          <span className="block">LandLekha नकल पर छपे QR कोड की ओर कैमरा दिखाएँ।</span></p>
        {!supported && <p className="mt-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">
          This browser cannot scan a code on this page. Open the extract's QR with your phone's own camera app instead.
          <span className="block">यह ब्राउज़र यहाँ कोड स्कैन नहीं कर सकता। अपने फ़ोन के कैमरा ऐप से QR कोड खोलें।</span></p>}
        {error === 'camera' && <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-bad">
          Could not access the camera. Check camera permission for this site and try again.
          <span className="block">कैमरा तक पहुँच नहीं मिली। इस साइट के लिए कैमरा अनुमति जाँचें और फिर कोशिश करें।</span></p>}
        <div className={`mt-4 overflow-hidden rounded-xl bg-slate-900 ${scanning ? '' : 'hidden'}`}>
          <video ref={videoRef} className="w-full" muted playsInline />
        </div>
        {supported && !scanning && <button type="button" className="btn-primary mt-4 w-full" onClick={start}>
          <QrCode size={16} /> Scan QR code · QR कोड स्कैन करें
        </button>}
      </div>
    </div>
  </main>
}

// the two reasons backend/api/routes/public.py gives for a failed check
const REASON_HI = {
  'no such record': 'ऐसा कोई अभिलेख नहीं है',
  'the record has changed since this extract was issued, or the extract is not genuine': 'नकल जारी होने के बाद अभिलेख बदल गया है, या यह नकल असली नहीं है',
}

// A citizen who scans this QR code may not read well - a phone reads it aloud instead.
// No server round-trip: the browser's own text-to-speech, in the language the record is
// already shown in on this page.
function speakText(res, lang) {
  const owners = res.owners.join(lang === 'hi' ? ' और ' : ' and ')
  const khasra = res.khasra_numbers.join(', ')
  return lang === 'hi'
    ? `यह एक असली और वर्तमान अभिलेख है। ग्राम ${res.location.village}, तहसील ${res.location.tehsil}, ज़िला ${res.location.district}, राज्य ${res.location.state}। खाता संख्या ${res.khata_number}। खसरा संख्या ${khasra}। खातेदार: ${owners}।`
    : `This is a genuine and up to date record. Village ${res.location.village}, tehsil ${res.location.tehsil}, district ${res.location.district}, state ${res.location.state}. Khata number ${res.khata_number}. Khasra number ${khasra}. Owner: ${owners}.`
}

function ReadAloud({ res }) {
  const [speaking, setSpeaking] = useState(null) // 'en' | 'hi' | null
  const supported = typeof window !== 'undefined' && 'speechSynthesis' in window
  useEffect(() => () => window.speechSynthesis?.cancel(), [])
  if (!supported) return null

  const speak = (lang) => {
    window.speechSynthesis.cancel()
    if (speaking === lang) { setSpeaking(null); return }
    const u = new SpeechSynthesisUtterance(speakText(res, lang))
    u.lang = lang === 'hi' ? 'hi-IN' : 'en-IN'
    u.onend = () => setSpeaking(null)
    u.onerror = () => setSpeaking(null)
    setSpeaking(lang)
    window.speechSynthesis.speak(u)
  }
  return <div className="mt-4 flex gap-2">
    <button type="button" className="btn-outline flex-1" onClick={() => speak('hi')}>
      {speaking === 'hi' ? <VolumeX size={15} /> : <Volume2 size={15} />} हिंदी में सुनें
    </button>
    <button type="button" className="btn-outline flex-1" onClick={() => speak('en')}>
      {speaking === 'en' ? <VolumeX size={15} /> : <Volume2 size={15} />} Read in English
    </button>
  </div>
}

// Public page opened by the QR code on a printed extract. No login needed.
export default function Verify() {
  const { id } = useParams()
  const [params] = useSearchParams()
  const [res, setRes] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.publicVerify(id, params.get('fp') || '').then(setRes).catch(setError)
  }, [id, params])
  useEffect(() => { document.title = 'Extract verification · अभिलेख सत्यापन · LandLekha' }, [])

  return <main className="min-h-full bg-slate-50 p-6">
    <div className="mx-auto max-w-lg">
      <div className="mb-6"><Logo /></div>
      <div className="card p-6">
        <h1 className="text-lg font-semibold text-slate-900">Extract verification · अभिलेख सत्यापन</h1>
        {error && <p className="mt-3 text-sm text-bad">Could not reach the records service. Try again later.
          <span className="block">अभिलेख सेवा से संपर्क नहीं हो सका। थोड़ी देर बाद फिर कोशिश करें।</span></p>}
        {!res && !error && <div className="mt-6 flex justify-center"><Spinner /></div>}
        {res?.valid && <>
          <div className="mt-4 flex items-center gap-2 rounded-lg bg-emerald-50 p-3 text-emerald-900">
            <CheckCircle2 size={22} /> <div><div className="font-semibold">Genuine and up to date · सही और वर्तमान</div>
              <div className="text-sm">This extract matches record #{res.record_id} as it stands today.</div>
              <div className="text-sm">यह नकल आज की स्थिति में अभिलेख #{res.record_id} से मेल खाती है।</div></div>
          </div>
          {/* citizens open this from a QR code on any phone, so labels carry both languages */}
          <dl className="mt-4 grid grid-cols-3 gap-x-3 gap-y-2.5 text-sm">
            <dt className="text-slate-500">Location<div className="text-xs">स्थान</div></dt><dd className="col-span-2">{res.location.village}, {res.location.tehsil}, {res.location.district}, {res.location.state}</dd>
            <dt className="text-slate-500">Khata No.<div className="text-xs">खाता संख्या</div></dt><dd className="col-span-2 tabular-nums">{res.khata_number}</dd>
            <dt className="text-slate-500">Khasra No.<div className="text-xs">खसरा संख्या</div></dt><dd className="col-span-2 tabular-nums">{res.khasra_numbers.join(', ')}</dd>
            <dt className="text-slate-500">Owner(s)<div className="text-xs">खातेदार</div></dt><dd className="col-span-2">{res.owners.join(', ')}</dd>
            <dt className="text-slate-500">Fingerprint<div className="text-xs">फ़िंगरप्रिंट</div></dt><dd className="col-span-2 font-mono">{res.fingerprint_short}</dd>
          </dl>
          <ReadAloud res={res} />
        </>}
        {res && !res.valid && <div className="mt-4 flex items-center gap-2 rounded-lg bg-red-50 p-3 text-red-900">
          <XCircle size={22} /> <div><div className="font-semibold">Does not match · मेल नहीं खाता</div>
            <div className="text-sm">{res.reason}. Ask the tehsil office for a fresh extract.</div>
            <div className="text-sm">{REASON_HI[res.reason] ? `${REASON_HI[res.reason]}। ` : ''}तहसील कार्यालय से नई नकल लें।</div></div>
        </div>}
      </div>
    </div>
  </main>
}
