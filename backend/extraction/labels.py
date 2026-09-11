"""Label vocabulary: how each field is written on real records (Hindi and English).

Adding a new state format usually means adding aliases here, not new code.
"""
from .normalize import label_key

FIELD_ALIASES: dict[str, list[str]] = {
    "owner_name": ["खातेदार का नाम", "खातेदार", "भूमिस्वामी का नाम", "भूमि स्वामी", "रैयत का नाम",
                   "Name of Landowner", "Landowner", "Owner Name", "Owner"],
    "father_name": ["पिता / पति का नाम", "पिता का नाम", "पिता पति", "Father's Name", "Father / Husband", "Father"],
    "khata_number": ["खाता संख्या", "खाता सं", "खाता नं", "Khata No", "Khata Number", "Account No"],
    "khasra_number": ["खसरा संख्या", "खसरा नं", "गाटा संख्या", "Khasra No", "Khasra Number", "Plot No"],
    "survey_number": ["सर्वे संख्या", "सर्वे नं", "Survey No", "Survey Number", "Sy No"],
    "plot_area": ["क्षेत्रफल", "रकबा", "Plot Area", "Area"],
    "land_classification": ["भूमि का प्रकार", "भूमि वर्ग", "Land Classification", "Land Class", "Class of Land"],
    "village": ["ग्राम", "गाँव", "मौजा", "Village", "Mauza"],
    "tehsil": ["तहसील", "Tehsil", "Taluka"],
    "district": ["जिला", "जनपद", "District"],
    "state": ["राज्य", "State"],
    "mutation_number": ["नामांतरण संख्या", "नामान्तरण संख्या", "दाखिल खारिज संख्या", "Mutation No", "Mutation Entry No"],
    "mutation_date": ["नामांतरण दिनांक", "नामान्तरण दिनांक", "Mutation Date", "Date of Mutation"],
    "registration_number": ["पंजीकरण संख्या", "रजिस्ट्री संख्या", "Registration No", "Regn No"],
    "registration_date": ["पंजीकरण दिनांक", "रजिस्ट्री दिनांक", "Registration Date", "Date of Registration"],
}

# (field, alias as typed, normalised key)
ALIAS_INDEX: list[tuple[str, str, str]] = sorted(
    ((f, a, label_key(a)) for f, aliases in FIELD_ALIASES.items() for a in aliases),
    key=lambda t: -len(t[2]),
)

DOC_TYPES: list[tuple[str, list[str]]] = [
    ("khatauni", ["खतौनी", "khatauni"]),
    ("khasra_panchsala", ["खसरा पांचसाला", "khasra panchsala"]),
    ("jamabandi", ["जमाबंदी", "jamabandi"]),
    ("khatiyan", ["खतियान", "khatiyan"]),
    ("record_of_rights", ["record of rights", "अधिकार अभिलेख"]),
    ("particulars_form", ["विवरण प्रपत्र", "particulars form"]),
]

AREA_UNIT_WORDS: dict[str, list[str]] = {
    "hectare": ["हेक्टेयर", "हेक्टर", "hectare", "hectares", "ha"],
    "acre": ["एकड़", "एकड", "acre", "acres"],
    "bigha": ["बीघा", "बिघा", "bigha"],
    "sqm": ["वर्ग मीटर", "sq m", "sqm", "square metre", "square meter"],
}

LAND_CLASS_WORDS: dict[str, list[str]] = {
    "agricultural_irrigated": ["कृषि (सिंचित)", "कृषि सिंचित", "सिंचित", "Agricultural (Irrigated)", "Irrigated"],
    "agricultural_unirrigated": ["कृषि (असिंचित)", "कृषि असिंचित", "असिंचित", "Agricultural (Unirrigated)", "Unirrigated"],
    "residential_abadi": ["आबादी", "Residential (Abadi)", "Abadi", "Residential"],
    "barren": ["बंजर", "Barren"],
    "pasture": ["चरागाह", "Pasture"],
    "orchard": ["बाग", "Orchard"],
    "commercial": ["वाणिज्यिक", "Commercial"],
}
