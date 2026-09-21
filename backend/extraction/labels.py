"""Label vocabulary: how each field is written on real records (Hindi, Telugu and English).

Adding a new state format usually means adding aliases here, not new code.
"""
from .normalize import label_key

FIELD_ALIASES: dict[str, list[str]] = {
    "owner_name": ["खातेदार का नाम", "खातेदार", "भूमिस्वामी का नाम", "भूमि स्वामी", "रैयत का नाम",
                   "Name of Landowner", "Landowner", "Owner Name", "Owner",
                  "పట్టాదారు పేరు", "పట్టాదారు", "యజమాని పేరు", "రైతు పేరు", "కబ్జాదారు పేరు"],
    "father_name": ["पिता / पति का नाम", "पिता का नाम", "पिता पति", "Father's Name", "Father / Husband", "Father",
                   "తండ్రి పేరు", "తండ్రి / భర్త పేరు", "భర్త పేరు"],
    "khata_number": ["खाता संख्या", "खाता सं", "खाता नं", "Khata No", "Khata Number", "Account No",
                    "ఖాతా సంఖ్య", "ఖాతా నంబరు", "ఖాతా నెం"],
    "khasra_number": ["खसरा संख्या", "खसरा नं", "गाटा संख्या", "Khasra No", "Khasra Number", "Plot No"],
    "survey_number": ["सर्वे संख्या", "सर्वे नं", "Survey No", "Survey Number", "Sy No",
                     "సర్వే నంబరు", "సర్వే సంఖ్య", "సర్వే నెం"],
    "plot_area": ["क्षेत्रफल", "रकबा", "Plot Area", "Area",
                 "విస్తీర్ణం", "వైశాల్యం", "పరిమాణం"],
    "land_classification": ["भूमि का प्रकार", "भूमि वर्ग", "Land Classification", "Land Class", "Class of Land",
                           "భూమి రకం", "భూమి స్వభావం", "భూమి వర్గం"],
    "village": ["ग्राम", "गाँव", "मौजा", "Village", "Mauza",
               "గ్రామం", "గ్రామము"],
    "tehsil": ["तहसील", "Tehsil", "Taluka",
              "మండలం", "మండలము", "తాలూకా"],
    "district": ["जिला", "जनपद", "District",
                "జిల్లా"],
    "state": ["राज्य", "State",
             "రాష్ట్రం", "రాష్ట్రము"],
    "mutation_number": ["नामांतरण संख्या", "नामान्तरण संख्या", "दाखिल खारिज संख्या", "Mutation No", "Mutation Entry No",
                       "మ్యుటేషన్ సంఖ్య", "మార్పు సంఖ్య"],
    "mutation_date": ["नामांतरण दिनांक", "नामान्तरण दिनांक", "Mutation Date", "Date of Mutation",
                     "మ్యుటేషన్ తేదీ", "మార్పు తేదీ"],
    "registration_number": ["पंजीकरण संख्या", "रजिस्ट्री संख्या", "Registration No", "Regn No",
                           "రిజిస్ట్రేషన్ సంఖ్య", "నమోదు సంఖ్య"],
    "registration_date": ["पंजीकरण दिनांक", "रजिस्ट्री दिनांक", "Registration Date", "Date of Registration",
                         "రిజిస్ట్రేషన్ తేదీ", "నమోదు తేదీ"],
}

# (field, alias as typed, normalised key)
ALIAS_INDEX: list[tuple[str, str, str]] = sorted(
    ((f, a, label_key(a)) for f, aliases in FIELD_ALIASES.items() for a in aliases),
    key=lambda t: -len(t[2]),
)


AREA_UNIT_WORDS: dict[str, list[str]] = {
    "hectare": ["हेक्टेयर", "हेक्टर", "హెక్టారు", "hectare", "hectares", "ha"],
    "acre": ["एकड़", "एकड", "ఎకరం", "ఎకరాలు", "acre", "acres"],
    "gunta": ["గుంట", "గుంటలు", "gunta", "guntha"],
    "cent": ["సెంట్లు", "సెంటు", "cent", "cents"],
    "kanal": ["कनाल", "कनाल", "kanal", "kanals"],
    "marla": ["मरला", "marla", "marlas"],
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
