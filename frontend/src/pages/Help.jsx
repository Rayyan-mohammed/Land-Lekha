import { ClipboardCheck, FileUp, Keyboard, Printer, ShieldCheck, Upload } from 'lucide-react'
import { PageHeader } from '../components/ui'
import { useT } from '../i18n'

// every text is an [English, Hindi] pair; the page shows the one for the chosen language
const GUIDES = [
  [Upload, ['Operators', 'ऑपरेटर'], [
    ['Upload scans, PDFs or phone photos from the Upload page. Several files at once is fine.',
      'अपलोड पन्ने से स्कैन, PDF या फ़ोन की फ़ोटो अपलोड करें। एक साथ कई फ़ाइलें भी चलेंगी।'],
    ['Each file shows its progress. Digital PDFs from the land portal finish in about a second.',
      'हर फ़ाइल की प्रगति दिखती है। भू-अभिलेख पोर्टल की डिजिटल PDF लगभग एक सेकंड में पूरी होती है।'],
    ['If a photo is too blurred, you are told straight away. Retake it before the owner leaves the counter.',
      'फ़ोटो बहुत धुंधली हो तो तुरंत बताया जाता है। खातेदार के काउंटर से जाने से पहले फिर से फ़ोटो लें।'],
    ['On a computer you can also paste a screenshot with Ctrl+V. For a batch, a summary line shows how many were accepted, sent to a verifier or need a retake.',
      'कंप्यूटर पर Ctrl+V से स्क्रीनशॉट भी चिपका सकते हैं। कई फ़ाइलों पर एक सारांश पंक्ति बताती है कि कितनी स्वीकृत हुईं, जाँचकर्ता को गईं या फिर से फ़ोटो चाहिए।'],
  ]],
  [ClipboardCheck, ['Verifiers', 'जाँचकर्ता'], [
    ['The Review queue lists documents with at least one uncertain field, lowest confidence first.',
      'जाँच सूची में वे दस्तावेज़ हैं जिनमें कम से कम एक विवरण अनिश्चित है — सबसे कम विश्वसनीयता पहले।'],
    ['You only check what is flagged. The scan is on the left, with a box on every field; click a box to jump to it.',
      'आपको केवल संदिग्ध विवरण जाँचने हैं। बाईं ओर स्कैन है, हर विवरण पर एक बॉक्स; बॉक्स पर क्लिक करके सीधे उस विवरण पर जाएँ।'],
    ['Confirm, correct or reject each flagged field, then approve. Corrections are remembered and applied to future documents.',
      'हर संदिग्ध विवरण की पुष्टि करें, सुधारें या अस्वीकार करें, फिर स्वीकृत करें। सुधार याद रखे जाते हैं और आगे के दस्तावेज़ों पर लागू होते हैं।'],
  ]],
  [ShieldCheck, ['Administrators', 'प्रशासक'], [
    ['The Dashboard shows progress by state and district, accuracy, and what is waiting.',
      'डैशबोर्ड पर राज्य और जिलेवार प्रगति, शुद्धता और लंबित काम दिखते हैं।'],
    ['Users & roles: create accounts, change roles, reset passwords. Everything is recorded in the audit trail.',
      'उपयोगकर्ता और भूमिकाएँ: खाते बनाएँ, भूमिका बदलें, पासवर्ड बदलें। सब कुछ ऑडिट लॉग में दर्ज होता है।'],
  ]],
  [Printer, ['Verified extracts', 'सत्यापित नकल'], [
    ['From Records & GIS, open a record and print its extract. The QR code on it lets anyone check it is genuine and current.',
      'अभिलेख और मानचित्र से कोई अभिलेख खोलें और उसकी नकल छापें। उस पर बने QR कोड से कोई भी जाँच सकता है कि नकल असली और ताज़ा है।'],
  ]],
]

const COLOURS = [
  ['border-ok bg-emerald-50', ['Green', 'हरा'], ['confident: passed every check, above the auto-accept threshold', 'भरोसेमंद: हर जाँच पास, स्वतः स्वीकृति सीमा से ऊपर']],
  ['border-warn bg-amber-50', ['Amber', 'पीला'], ['please check: readable but not certain', 'कृपया जाँचें: पढ़ने योग्य, पर पक्का नहीं']],
  ['border-bad bg-red-50', ['Red', 'लाल'], ['probably wrong or failed a rule (format, master data)', 'शायद ग़लत, या किसी नियम (प्रारूप, मास्टर डेटा) पर खरा नहीं']],
]

const KEYS = [
  ['↑ ↓', ['move between fields', 'विवरणों के बीच जाएँ']], ['N', ['next flagged field', 'अगला संदिग्ध विवरण']],
  ['Enter', ['confirm the field', 'विवरण की पुष्टि']], ['X', ['reject the field', 'विवरण अस्वीकार']],
  ['E', ['edit the value', 'मान बदलें']], ['Ctrl + Enter', ['approve the record', 'अभिलेख स्वीकृत करें']],
  ['Esc', ['leave the text box', 'लिखने का बॉक्स छोड़ें']],
]

const FAQ = [
  [['Why was my photo marked "poor"?', 'मेरी फ़ोटो को "ख़राब" क्यों बताया गया?'],
    ['The text could not be read reliably, usually blur, shadow or a page that is too small in the frame. A clearer photo or the portal PDF fixes it; guessing would put wrong data into the record.',
      'लिखावट भरोसे से नहीं पढ़ी जा सकी — अक्सर धुंधलापन, छाया, या फ़्रेम में पन्ना बहुत छोटा होने से। साफ़ फ़ोटो या पोर्टल की PDF से यह ठीक होता है; अंदाज़ा लगाने से अभिलेख में ग़लत जानकारी चली जाती।']],
  [['What does the percentage mean?', 'प्रतिशत का क्या मतलब है?'],
    ['How likely the value is to be correct, learned from checked examples. Fields below the threshold always go to a person.',
      'मान के सही होने की संभावना, जो जाँचे गए उदाहरणों से सीखी गई है। सीमा से नीचे के विवरण हमेशा किसी व्यक्ति के पास जाते हैं।']],
  [['The village was not found. What now?', 'ग्राम नहीं मिला। अब क्या करें?'],
    ['Check the spelling against the official village list. If the village is genuinely missing, tell the administrator so the master list can be updated.',
      'आधिकारिक ग्राम सूची से वर्तनी मिलाएँ। अगर ग्राम सच में सूची में नहीं है, तो प्रशासक को बताएँ ताकि मास्टर सूची अपडेट हो सके।']],
  [['Can an approval be undone?', 'क्या स्वीकृति वापस ली जा सकती है?'],
    ['Not from the screen. Every approval is kept in the audit trail with who and when; an administrator can re-issue a corrected record.',
      'स्क्रीन से नहीं। हर स्वीकृति किसने और कब के साथ ऑडिट लॉग में रहती है; प्रशासक सुधरा हुआ अभिलेख फिर से जारी कर सकता है।']],
  [['How do I switch between Hindi and English?', 'हिंदी और अंग्रेज़ी के बीच कैसे बदलें?'],
    ['Click हिंदी / English at the bottom of the menu (or on the sign-in page). Every screen, message and date changes at once, and the choice is remembered on this computer.',
      'मेन्यू के नीचे (या लॉग इन पन्ने पर) हिंदी / English पर क्लिक करें। हर स्क्रीन, संदेश और तारीख तुरंत बदल जाती है, और यह चुनाव इस कंप्यूटर पर याद रहता है।']],
  [['Can I get the records into Excel?', 'क्या अभिलेख Excel में मिल सकते हैं?'],
    ['Yes. On Records & GIS, search if you like, then press CSV. The file opens in Excel with Hindi names shown correctly, one row per record with every co-owner and khasra.',
      'हाँ। अभिलेख और मानचित्र पर चाहें तो खोजें, फिर CSV दबाएँ। फ़ाइल Excel में खुलती है और हिंदी नाम सही दिखते हैं; हर अभिलेख की एक पंक्ति, सभी सह-खातेदार और खसरों के साथ।']],
  [['Why was I asked to sign in again?', 'मुझसे दोबारा लॉग इन करने को क्यों कहा गया?'],
    ['For safety, a sign-in lasts a limited time. Sign in again and you return to the page you were on; nothing you had saved is lost.',
      'सुरक्षा के लिए लॉग इन कुछ समय तक ही रहता है। दोबारा लॉग इन करें, आप उसी पन्ने पर लौट आएँगे; सहेजा हुआ कुछ भी नहीं खोता।']],
  [['What does "3 to check" mean?', '"3 जाँचने हैं" का क्या मतलब है?'],
    ['How many fields on that document still need a person: below the confidence threshold or failing a rule. On the review queue, choose "Fewest fields first" to clear the quick ones.',
      'उस दस्तावेज़ के कितने विवरण अभी किसी व्यक्ति को देखने हैं: जो विश्वसनीयता सीमा से नीचे हैं या किसी नियम पर खरे नहीं। जाँच सूची में "सबसे कम विवरण पहले" चुनें, जल्दी वाले पहले निपट जाएँगे।']],
  [['How do I send many records to LRMS at once?', 'कई अभिलेख एक साथ LRMS को कैसे भेजें?'],
    ['On Records & GIS, press "Not sent to LRMS", then "Send all to LRMS". Each record is sent in turn and one message tells you how many went through.',
      'अभिलेख और मानचित्र पर "LRMS को नहीं भेजे" दबाएँ, फिर "सभी LRMS को भेजें"। हर अभिलेख बारी-बारी से भेजा जाता है और एक संदेश बताता है कि कितने गए।']],
  [['What if I close the tab in the middle of a review?', 'अगर जाँच के बीच टैब बंद हो जाए तो?'],
    ['Your corrections are kept on this computer for a day. Open the same document again and they come back; approve when you are ready. To move on without deciding, press Skip.',
      'आपके सुधार इस कंप्यूटर पर एक दिन तक रखे जाते हैं। वही दस्तावेज़ फिर खोलें, वे वापस आ जाएँगे; तैयार होने पर स्वीकृत करें। बिना निर्णय आगे बढ़ना हो तो छोड़ें दबाएँ।']],
]

export default function Help() {
  const { t, lang } = useT()
  const L = ([en, hi]) => (lang === 'hi' ? hi : en)
  return <div className="space-y-4">
    <PageHeader title={t('Help')} subtitle={L(['How LandLekha works, in two minutes', 'LandLekha कैसे काम करता है, दो मिनट में'])} />
    <div className="grid gap-4 md:grid-cols-2">
      {GUIDES.map(([Icon, title, points]) => <section key={title[0]} className="card p-4">
        <h2 className="flex items-center gap-2 font-medium text-slate-900"><Icon size={17} className="text-brand-600" /> {L(title)}</h2>
        <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm text-slate-700">{points.map((p) => <li key={p[0]}>{L(p)}</li>)}</ul>
      </section>)}
    </div>
    <div className="grid gap-4 md:grid-cols-2">
      <section className="card p-4">
        <h2 className="font-medium text-slate-900">{L(['What the colours mean', 'रंगों का मतलब'])}</h2>
        <ul className="mt-2 space-y-2 text-sm">{COLOURS.map(([cls, name, text]) => <li key={name[0]} className="flex items-center gap-2.5">
          <span className={`h-4 w-4 shrink-0 rounded-sm border-2 ${cls}`} /><span><span className="font-medium">{L(name)}</span>: {L(text)}</span></li>)}</ul>
      </section>
      <section className="card p-4">
        <h2 className="flex items-center gap-2 font-medium text-slate-900"><Keyboard size={17} className="text-brand-600" /> {L(['Review shortcuts', 'जाँच के शॉर्टकट'])}</h2>
        <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-sm">
          {KEYS.map(([k, what]) => <div key={k} className="contents"><dt><kbd className="kbd">{k}</kbd></dt><dd className="text-slate-700">{L(what)}</dd></div>)}
        </dl>
      </section>
    </div>
    <section className="card p-4">
      <h2 className="flex items-center gap-2 font-medium text-slate-900"><FileUp size={17} className="text-brand-600" /> {L(['Common questions', 'आम सवाल'])}</h2>
      <div className="mt-2 divide-y divide-slate-100">{FAQ.map(([q, a]) => <details key={q[0]} className="group py-2.5">
        <summary className="text-sm font-medium text-slate-800 marker:text-brand-600">{L(q)}</summary>
        <p className="mt-1.5 text-sm text-slate-600">{L(a)}</p>
      </details>)}</div>
    </section>
  </div>
}
