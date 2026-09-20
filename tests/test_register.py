"""Cross-checking a read record against the simulated state register."""
from backend.integration.register import Register, compare

HELD = {"village": "Nigohan", "tehsil": "Mohanlalganj", "district": "Lucknow",
        "khata_number": "00245", "khasra_number": "123/2",
        "owner_name": "Ram Prasad Sharma", "father_name": "Mohan Lal Sharma",
        "plot_area": "0.412 hectare", "land_classification": "agricultural_irrigated"}


def _register():
    reg = Register()
    reg.add(HELD)
    return reg


def test_a_record_that_matches_the_register_says_so():
    result = compare(HELD, _register().find(HELD))
    assert result["found"] and result["differ"] == 0
    assert result["summary"] == "matches the register"
    assert result["simulated"] is True          # never presented as proof of anything


def test_a_different_owner_is_reported_with_both_values():
    """The point of the check: the paper can be right and still be out of date."""
    mine = {**HELD, "owner_name": "Shyam Lal Verma"}
    result = compare(mine, _register().find(mine))
    owner = result["fields"]["owner_name"]
    assert owner["status"] == "differ"
    assert owner["ours"] == "Shyam Lal Verma" and owner["register"] == "Ram Prasad Sharma"
    assert result["differ"] == 1 and "1 field differ" in result["summary"]


def test_nothing_is_corrected_or_overwritten():
    mine = {**HELD, "plot_area": "0.500 hectare"}
    result = compare(mine, _register().find(mine))
    assert result["fields"]["plot_area"]["ours"] == "0.500 hectare"   # our reading is untouched


def test_a_parcel_the_register_does_not_hold():
    mine = {**HELD, "khasra_number": "999/9"}
    result = compare(mine, _register().find(mine))
    assert result["found"] is False and result["summary"] == "no matching parcel in the register"
    assert result["fields"] == {}


def test_spacing_and_case_are_not_disagreements():
    mine = {**HELD, "owner_name": "  ram prasad   SHARMA "}
    assert compare(mine, _register().find(mine))["differ"] == 0


def test_a_field_the_register_does_not_carry_is_not_a_disagreement():
    reg = Register()
    reg.add({k: v for k, v in HELD.items() if k != "father_name"})
    result = compare(HELD, reg.find(HELD))
    assert result["fields"]["father_name"]["status"] == "not_held"
    assert result["differ"] == 0


def test_the_lookup_ignores_case_and_padding_in_the_village():
    reg = _register()
    assert reg.find({**HELD, "village": " nigohan "}) is not None


def test_a_saved_register_reloads(tmp_path):
    path = tmp_path / "register.json"
    _register().save(path)
    again = Register.load(path)
    assert len(again.entries) == 1
    assert compare(HELD, again.find(HELD))["differ"] == 0
