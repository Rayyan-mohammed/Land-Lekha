// Hindi / English interface text for the operator and verifier screens.
// Field names are already bilingual (constants.js); this covers the surrounding UI.
import { createContext, useContext, useEffect, useState } from 'react'

const HI = {
  // menu
  'Upload': 'अपलोड',
  'Documents': 'दस्तावेज़',
  'Review queue': 'जाँच सूची',
  'Dashboard': 'डैशबोर्ड',
  'Records & GIS': 'अभिलेख और मानचित्र',
  'Audit trail': 'ऑडिट लॉग',
  'Users': 'उपयोगकर्ता',
  'Sign out': 'लॉग आउट',
  'Land record digitization': 'भूमि अभिलेख डिजिटलीकरण',
  // login
  'Sign in': 'लॉग इन',
  'Use your department account.': 'अपने विभागीय खाते से लॉग इन करें।',
  'Username': 'उपयोगकर्ता नाम',
  'Password': 'पासवर्ड',
  'Signing in…': 'लॉग इन हो रहा है…',
  'Demo accounts': 'डेमो खाते',
  // upload
  'Upload land records': 'भूमि अभिलेख अपलोड करें',
  'Scanned PDFs, images or phone photos · Hindi and English · printed or handwritten': 'स्कैन PDF, चित्र या मोबाइल फ़ोटो · हिंदी और अंग्रेज़ी · छपे या हस्तलिखित',
  'Drop files here': 'फ़ाइलें यहाँ छोड़ें',
  'PNG, JPG, TIFF or PDF, up to 20 MB each': 'PNG, JPG, TIFF या PDF, प्रत्येक 20 MB तक',
  'Choose files': 'फ़ाइलें चुनें',
  'Take photo': 'फ़ोटो लें',
  'Uploading…': 'अपलोड हो रहा है…',
  'Reading document (preprocessing → OCR → field extraction)…': 'दस्तावेज़ पढ़ा जा रहा है (सुधार → OCR → विवरण निकालना)…',
  'Could not process this file': 'यह फ़ाइल संसाधित नहीं हो सकी',
  'Unknown district': 'अज्ञात जिला',
  'processed in': 'संसाधित',
  'Open': 'खोलें',
  'Image too poor to read reliably — please retake': 'चित्र साफ़ नहीं है — कृपया दोबारा फ़ोटो लें',
  'open existing': 'पहले वाला खोलें',
  'In queue': 'कतार में',
  'Reading and checking': 'पढ़ा और जाँचा जा रहा है',
  'Done': 'पूर्ण',
  'usually 10–30 seconds per page; digital PDFs about a second': 'आमतौर पर प्रति पृष्ठ 10–30 सेकंड; डिजिटल PDF लगभग 1 सेकंड',
  // lists
  'Refresh': 'रीफ़्रेश',
  'Search file name or district': 'फ़ाइल नाम या जिला खोजें',
  'All statuses': 'सभी स्थितियाँ',
  'File': 'फ़ाइल',
  'Type': 'प्रकार',
  'District': 'जिला',
  'Status': 'स्थिति',
  'Confidence': 'विश्वसनीयता',
  'Time': 'समय',
  'Uploaded': 'अपलोड',
  'Review': 'जाँचें',
  'Start reviewing': 'जाँच शुरू करें',
  'Documents with at least one uncertain field — lowest confidence first': 'जिन दस्तावेज़ों में कम से कम एक विवरण अनिश्चित है — सबसे कम विश्वसनीयता पहले',
  'Nothing waiting. Every processed document is either verified or passed automatically.': 'कुछ भी लंबित नहीं है। सभी दस्तावेज़ सत्यापित या स्वतः स्वीकृत हैं।',
  'Previous': 'पिछला',
  'Next': 'अगला',
  // review screen
  'Extracted fields': 'निकाले गए विवरण',
  'flagged': 'संदिग्ध',
  'auto-accept': 'स्वतः स्वीकृति',
  'Why this needs a human': 'इसे जाँच की ज़रूरत क्यों है',
  'Possible duplicate of existing record': 'मौजूदा अभिलेख की संभावित प्रति',
  'The image is too poor to read reliably — please rescan or retake it': 'चित्र साफ़ पढ़ने योग्य नहीं है — कृपया दोबारा स्कैन करें या फ़ोटो लें',
  'Image quality is only fair — check the flagged fields carefully': 'चित्र की गुणवत्ता औसत है — संदिग्ध विवरण ध्यान से जाँचें',
  'Co-owners on this khata': 'इस खाते के सह-खातेदार',
  'Parcels under this khata': 'इस खाते के खसरा',
  'Master data checks': 'मास्टर डेटा जाँच',
  'Note for the audit trail (optional)': 'ऑडिट लॉग के लिए टिप्पणी (वैकल्पिक)',
  'Approve record': 'अभिलेख स्वीकृत करें',
  'Reject': 'अस्वीकार करें',
  'Unmarked fields are confirmed as shown. Corrections are remembered and applied to future documents.':
    'जिन विवरणों को नहीं बदला गया वे जैसे हैं वैसे ही स्वीकृत होंगे। सुधार याद रखे जाते हैं और आगे के दस्तावेज़ों पर लागू होते हैं।',
  'Audit trail for this document': 'इस दस्तावेज़ का ऑडिट लॉग',
  'not found — type to add': 'नहीं मिला — लिखकर जोड़ें',
  'OCR read': 'OCR ने पढ़ा',
  'Re-run': 'फिर से चलाएँ',
  'Record': 'अभिलेख',
  // statuses
  'Queued': 'कतार में',
  'Processing': 'संसाधन जारी',
  'Auto-accepted': 'स्वतः स्वीकृत',
  'Needs review': 'जाँच आवश्यक',
  'Verified': 'सत्यापित',
  'Rejected': 'अस्वीकृत',
  'Failed': 'विफल',
  'Good image': 'चित्र अच्छा',
  'Fair image': 'चित्र औसत',
  'Poor image — retake': 'चित्र ख़राब — दोबारा लें',
}

const KEY = 'landlekha.lang'
const LangContext = createContext({ lang: 'en', setLang: () => {}, t: (s) => s })

export function LangProvider({ children }) {
  const [lang, setLang] = useState(() => {
    try { return localStorage.getItem(KEY) || 'en' } catch { return 'en' }
  })
  useEffect(() => {
    try { localStorage.setItem(KEY, lang) } catch { /* private mode */ }
    document.documentElement.lang = lang
  }, [lang])
  const t = (s) => (lang === 'hi' && HI[s]) || s
  return <LangContext.Provider value={{ lang, setLang, t }}>{children}</LangContext.Provider>
}

export const useT = () => useContext(LangContext)

export function LangToggle({ className = '' }) {
  const { lang, setLang } = useT()
  return <button type="button" onClick={() => setLang(lang === 'hi' ? 'en' : 'hi')}
    className={`rounded-md border px-2 py-1 text-xs font-medium ${className}`}
    title={lang === 'hi' ? 'Switch to English' : 'हिंदी में देखें'}>
    {lang === 'hi' ? 'English' : 'हिंदी'}
  </button>
}
