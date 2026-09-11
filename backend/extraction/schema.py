"""Canonical land-record field schema shared by extraction, backend and eval.

Every extracted document is mapped onto these fields. `required` fields must be
present and confident for a document to be auto-accepted.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class FieldDef:
    name: str
    label_en: str
    label_hi: str
    kind: str  # name | id | area | place | date | category | text
    required: bool = False


FIELDS: list[FieldDef] = [
    FieldDef("owner_name", "Landowner Name", "खातेदार का नाम", "name", required=True),
    FieldDef("father_name", "Father / Husband Name", "पिता / पति का नाम", "name"),
    FieldDef("khata_number", "Khata No.", "खाता संख्या", "id", required=True),
    FieldDef("khasra_number", "Khasra No.", "खसरा संख्या", "id", required=True),
    FieldDef("survey_number", "Survey No.", "सर्वे संख्या", "id"),
    FieldDef("plot_area", "Plot Area", "क्षेत्रफल", "area", required=True),
    FieldDef("land_classification", "Land Classification", "भूमि का प्रकार", "category"),
    FieldDef("village", "Village", "ग्राम", "place", required=True),
    FieldDef("tehsil", "Tehsil", "तहसील", "place", required=True),
    FieldDef("district", "District", "जिला", "place", required=True),
    FieldDef("state", "State", "राज्य", "place"),
    FieldDef("mutation_number", "Mutation No.", "नामांतरण संख्या", "id"),
    FieldDef("mutation_date", "Mutation Date", "नामांतरण दिनांक", "date"),
    FieldDef("registration_number", "Registration No.", "पंजीकरण संख्या", "id"),
    FieldDef("registration_date", "Registration Date", "पंजीकरण दिनांक", "date"),
]

FIELD_MAP: dict[str, FieldDef] = {f.name: f for f in FIELDS}
FIELD_NAMES: list[str] = [f.name for f in FIELDS]
REQUIRED_FIELDS: list[str] = [f.name for f in FIELDS if f.required]

# canonical land classes: key -> (english, hindi)
LAND_CLASSES: dict[str, tuple[str, str]] = {
    "agricultural_irrigated": ("Agricultural (Irrigated)", "कृषि (सिंचित)"),
    "agricultural_unirrigated": ("Agricultural (Unirrigated)", "कृषि (असिंचित)"),
    "residential_abadi": ("Residential (Abadi)", "आबादी"),
    "barren": ("Barren", "बंजर"),
    "pasture": ("Pasture", "चरागाह"),
    "orchard": ("Orchard", "बाग"),
    "commercial": ("Commercial", "वाणिज्यिक"),
}

# area units -> hectares multiplier (bigha is state specific, see master data)
AREA_UNITS: dict[str, float] = {
    "hectare": 1.0,
    "acre": 0.404686,
    "sqm": 0.0001,
    "bigha": 0.2529,
}
