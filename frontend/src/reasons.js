// Turns the backend's routing reasons ("low confidence: owner_name (0.55)") into plain
// sentences in the viewer's language. Unknown formats are shown as they are.
import { FIELD_MAP } from './constants'

const field = (name, lang) => (FIELD_MAP[name] ? (lang === 'hi' ? FIELD_MAP[name].hi : FIELD_MAP[name].en) : name)

const CHECKS = {
  district_in_state: ['district does not belong to this state', 'जिला इस राज्य का नहीं है'],
  tehsil_in_district: ['tehsil does not belong to this district', 'तहसील इस जिले की नहीं है'],
  village_in_tehsil: ['village does not belong to this tehsil', 'ग्राम इस तहसील का नहीं है'],
}

export function explainReason(r, lang = 'en') {
  const hi = lang === 'hi'
  let m
  if ((m = r.match(/^low confidence: (\w+) \(([\d.]+)\)$/))) {
    const pct = Math.round(parseFloat(m[2]) * 100)
    return hi ? `${field(m[1], lang)}: पढ़ाई पर भरोसा कम (${pct}%)` : `${field(m[1], lang)}: not sure of the reading (${pct}%)`
  }
  if ((m = r.match(/^missing required field: (\w+)$/))) {
    return hi ? `${field(m[1], lang)}: पन्ने पर नहीं मिला` : `${field(m[1], lang)}: not found on the page`
  }
  if ((m = r.match(/^invalid (\w+): (.+)$/))) {
    return hi ? `${field(m[1], lang)}: नियम पर खरा नहीं (${m[2]})` : `${field(m[1], lang)}: fails a check (${m[2]})`
  }
  if ((m = r.match(/^consistency failed: (\w+) \((.+)\)$/))) {
    const c = CHECKS[m[1]]
    return c ? `${hi ? c[1] : c[0]} (${m[2]})` : r
  }
  if ((m = r.match(/^possible duplicate of record (\d+) \((.+)\)$/))) {
    return hi ? `अभिलेख #${m[1]} जैसा लगता है (${m[2]})` : `looks like existing record #${m[1]} (${m[2]})`
  }
  return r
}

// Photo-quality advice from backend/ocr/quality.py, in the viewer's language.
const ADVICE = [
  [/^very little text found/, 'बहुत कम लिखावट मिली — जाँचें कि यह भू-अभिलेख का पन्ना है'],
  [/^image is blurred/, 'चित्र धुंधला है — कैमरा स्थिर रखें, फ़ोकस के लिए स्क्रीन छुएँ और फिर से फ़ोटो लें'],
  [/^text is small/, 'अक्षर छोटे हैं — कैमरा पास लाएँ या 300 dpi पर स्कैन करें'],
  [/^text is hard to read/, 'पढ़ना कठिन है — बराबर रोशनी में फिर से फ़ोटो लें, या पन्ना स्कैन करें'],
]

export function explainAdvice(a, lang = 'en') {
  if (lang !== 'hi') return a
  const m = a.match(/^low resolution \((\d+)px\) - use at least (\d+)px/)
  if (m) return `कम रिज़ॉल्यूशन (${m[1]}px) — कम से कम ${m[2]}px / 150 dpi रखें`
  const hit = ADVICE.find(([re]) => re.test(a))
  return hit ? hit[1] : a
}
