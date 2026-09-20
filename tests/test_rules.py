"""The cross-field rule catalogue: ids, explanations, and the checks themselves."""
from backend.extraction.rules import RULES, check_areas, check_dates, explain


def test_every_rule_reads_in_both_languages():
    for rid, rule in RULES.items():
        assert rule.id == rid
        assert rule.en and rule.hi and rule.en != rule.hi
        assert any("\u0900" <= ch <= "\u097f" for ch in rule.hi), f"{rid} has no Hindi"


def test_an_old_check_name_still_explains_itself():
    """Documents checked before the ids existed keep their meaning."""
    assert explain("tehsil_in_district") == explain("LOC-2")
    assert explain("village_in_tehsil", "hi") == explain("LOC-3", "hi")


def test_an_unknown_check_is_passed_through_not_invented():
    assert explain("SOMETHING-NEW") == "SOMETHING-NEW"


def test_a_mutation_cannot_predate_its_registration():
    fields = {"mutation_date": {"normalized": {"iso": "2015-03-12"}},
              "registration_date": {"normalized": {"iso": "2019-07-31"}}}
    date1 = next(c for c in check_dates(fields) if c["check"] == "DATE-1")
    assert date1["ok"] is False
    assert "2015-03-12" in date1["detail"] and "2019-07-31" in date1["detail"]


def test_dates_in_the_right_order_pass():
    fields = {"mutation_date": {"normalized": {"iso": "2019-08-01"}},
              "registration_date": {"normalized": {"iso": "2019-07-31"}}}
    assert next(c for c in check_dates(fields) if c["check"] == "DATE-1")["ok"] is True


def test_a_date_in_the_future_is_caught():
    fields = {"mutation_date": {"normalized": {"iso": "2099-01-01"}}}
    assert any(c["check"] == "DATE-2" and not c["ok"] for c in check_dates(fields))


def test_a_missing_or_unparsable_date_raises_nothing():
    assert check_dates({}) == []
    assert check_dates({"mutation_date": {"normalized": {"iso": "not a date"}}}) == []


def test_khasra_rows_that_do_not_add_up_are_flagged():
    """A row lost to a bad read shows up as a shortfall instead of passing unnoticed."""
    fields = {"plot_area": {"normalized": {"hectares": 2.0}}}
    parcels = [{"plot_area_normalized": {"hectares": 0.5}}, {"plot_area_normalized": {"hectares": 0.6}}]
    check = next(c for c in check_areas(fields, parcels) if c["check"] == "AREA-2")
    assert check["ok"] is False and "2 rows" in check["detail"]


def test_rounding_slack_does_not_trip_the_area_rule():
    fields = {"plot_area": {"normalized": {"hectares": 1.0}}}
    parcels = [{"plot_area_normalized": {"hectares": 0.501}}, {"plot_area_normalized": {"hectares": 0.502}}]
    assert next(c for c in check_areas(fields, parcels) if c["check"] == "AREA-2")["ok"] is True


def test_a_single_row_is_not_compared_with_itself():
    fields = {"plot_area": {"normalized": {"hectares": 1.0}}}
    assert check_areas(fields, [{"plot_area_normalized": {"hectares": 1.0}}]) == []
