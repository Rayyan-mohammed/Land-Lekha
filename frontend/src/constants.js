// Mirrors backend/extraction/schema.py
export const FIELDS = [
  { name: 'owner_name', en: 'Landowner Name', hi: 'खातेदार का नाम', required: true },
  { name: 'father_name', en: 'Father / Husband', hi: 'पिता / पति का नाम' },
  { name: 'khata_number', en: 'Khata No.', hi: 'खाता संख्या', required: true },
  { name: 'khasra_number', en: 'Khasra No.', hi: 'खसरा संख्या', required: true },
  { name: 'survey_number', en: 'Survey No.', hi: 'सर्वे संख्या' },
  { name: 'plot_area', en: 'Plot Area', hi: 'क्षेत्रफल', required: true },
  { name: 'land_classification', en: 'Land Class', hi: 'भूमि का प्रकार' },
  { name: 'village', en: 'Village', hi: 'ग्राम', required: true },
  { name: 'tehsil', en: 'Tehsil', hi: 'तहसील', required: true },
  { name: 'district', en: 'District', hi: 'जिला', required: true },
  { name: 'state', en: 'State', hi: 'राज्य' },
  { name: 'mutation_number', en: 'Mutation No.', hi: 'नामांतरण संख्या' },
  { name: 'mutation_date', en: 'Mutation Date', hi: 'नामांतरण दिनांक' },
  { name: 'registration_number', en: 'Registration No.', hi: 'पंजीकरण संख्या' },
  { name: 'registration_date', en: 'Registration Date', hi: 'पंजीकरण दिनांक' },
]
export const FIELD_MAP = Object.fromEntries(FIELDS.map((f) => [f.name, f]))

export const LAND_CLASSES = {
  agricultural_irrigated: 'Agricultural (Irrigated) · कृषि (सिंचित)',
  agricultural_unirrigated: 'Agricultural (Unirrigated) · कृषि (असिंचित)',
  residential_abadi: 'Residential (Abadi) · आबादी',
  barren: 'Barren · बंजर',
  pasture: 'Pasture · चरागाह',
  orchard: 'Orchard · बाग',
  commercial: 'Commercial · वाणिज्यिक',
}

export const STATUS = {
  queued: { label: 'Queued', cls: 'bg-slate-100 text-slate-700' },
  processing: { label: 'Processing', cls: 'bg-sky-100 text-sky-800' },
  auto_accepted: { label: 'Auto-accepted', cls: 'bg-emerald-100 text-emerald-800' },
  needs_review: { label: 'Needs review', cls: 'bg-amber-100 text-amber-800' },
  verified: { label: 'Verified', cls: 'bg-green-100 text-green-800' },
  rejected: { label: 'Rejected', cls: 'bg-red-100 text-red-800' },
  failed: { label: 'Failed', cls: 'bg-red-100 text-red-800' },
}

export const ROLE_LABEL = { operator: 'Operator', verifier: 'Verifier', admin: 'Administrator' }
