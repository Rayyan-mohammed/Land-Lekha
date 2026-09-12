"""Word lists for the land-document classifier, grouped by what kind of evidence they are.

Grouping is the point. A page is not a land record because it says "survey" once; it is one
because it carries several *different* kinds of land-record evidence at the same time - a
parcel identifier, an extent, a revenue office, a tenure word. Each group below is one kind.

Terms are matched case-folded against the OCR text of the page, in Devanagari, Telugu and
Latin script where the word is commonly written that way. This is a vocabulary, not a
template: no layout or field order is assumed.
"""
from __future__ import annotations

# --- land evidence, by kind ------------------------------------------------------------
PARCEL_ID = [
    "khasra", "खसरा", "khata", "खाता", "khatauni", "खतौनी", "khatiyan", "खतियान",
    "survey no", "survey number", "सर्वे", "సర్వే", "patta", "पट्टा", "పట్టా",
    "jamabandi", "जमाबंदी", "pahani", "పహాణి", "adangal", "ఆదంగల్", "gat number", "hissa",
    "plot no", "plot number", "भूखंड", "naksha", "नक्शा", "cadastral",
]
EXTENT = [
    "hectare", "हेक्टेयर", "हेक्टर", "acre", "एकड़", "एकड", "ఎకరం", "bigha", "बीघा",
    "biswa", "बिस्वा", "gunta", "guntha", "గుంట", "cents", "సెంట్లు", "area", "क्षेत्रफल",
    "extent", "విస్తీర్ణం", "sq mtr", "square metre", "वर्ग मीटर",
]
TENURE = [
    "khatedar", "खातेदार", "pattadar", "పట్టాదారు", "bhumidhar", "भूमिधर", "landowner",
    "land owner", "owner name", "स्वामी", "occupant", "काश्तकार", "cultivator", "tenant",
    "possession", "कब्जा", "ownership", "स्वामित्व",
]
REVENUE_OFFICE = [
    "tehsil", "तहसील", "tahsil", "taluk", "taluka", "mandal", "मंडल", "మండలం",
    "patwari", "पटवारी", "lekhpal", "लेखपाल", "village accountant", "revenue department",
    "राजस्व विभाग", "tahsildar", "tehsildar", "तहसीलदार", "mandal revenue office",
    "halka", "हल्का", "circle officer", "kanungo", "कानूनगो",
]
LAND_USE = [
    "irrigated", "सिंचित", "unirrigated", "असिंचित", "agricultural", "कृषि", "వ్యవసాయ",
    "barren", "बंजर", "abadi", "आबादी", "orchard", "बाग", "wet land", "dry land",
    "land classification", "भूमि का प्रकार", "nature of land",
]
BOUNDARY = [
    "chauhaddi", "चौहद्दी", "boundaries", "सीमा", "east", "पूर्व", "west", "पश्चिम",
    "north", "उत्तर", "south", "दक्षिण", "adjoining", "abutting",
]
TRANSACTION = [
    "sale deed", "विक्रय पत्र", "gift deed", "दान पत्र", "lease deed", "पट्टा विलेख",
    "partition deed", "विभाजन", "exchange deed", "mortgage", "बंधक", "mutation",
    "नामांतरण", "दाखिल खारिज", "registration no", "पंजीकरण", "sub registrar",
    "उप निबंधक", "vendor", "vendee", "donor", "donee", "consideration", "प्रतिफल",
    "conveyance", "transfer of property",
]

LAND_GROUPS: dict[str, list[str]] = {
    "parcel identifier": PARCEL_ID,
    "extent": EXTENT,
    "tenure": TENURE,
    "revenue office": REVENUE_OFFICE,
    "land use": LAND_USE,
    "boundaries": BOUNDARY,
    "transaction": TRANSACTION,
}

# --- government indicators: reported, never treated as proof of anything ----------------
GOVERNMENT = [
    "government of", "भारत सरकार", "सरकार", "ప్రభుత్వం", "revenue department",
    "registration department", "district administration", "collector", "कलेक्टर",
    "government of india", "state government", "राज्य सरकार", "seal", "मुहर",
]

# --- things that are emphatically not land records --------------------------------------
NOT_LAND = {
    "invoice": ["invoice", "gstin", "tax invoice", "bill to", "payment terms", "total due",
                "purchase order", "hsn", "चालान", "बीजक"],
    "certificate": ["certificate", "marksheet", "mark sheet", "examination", "roll no",
                    "university", "board of secondary", "grade", "semester", "प्रमाण पत्र",
                    "विश्वविद्यालय", "birth certificate", "caste certificate"],
    "bank": ["account statement", "ifsc", "branch code", "closing balance", "debit", "credit card",
             "transaction id", "cheque", "passbook", "बैंक"],
    "news": ["newspaper", "correspondent", "headline", "edition", "reuters", "press trust",
             "समाचार", "संवाददाता"],
    "identity": ["aadhaar", "आधार", "passport", "driving licence", "driving license",
                 "voter id", "pan card", "permanent account number"],
    "medical": ["prescription", "diagnosis", "patient", "hospital", "mg tablet", "dosage"],
}
