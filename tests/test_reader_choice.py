"""Choosing the reader by reading a little of the page with each candidate."""
from backend.ocr.scripts import MIN_ABSOLUTE, MIN_GAIN, choose_reader


class FakeEngine:
    """Answers with a fixed confidence per language set, and counts what it was asked."""

    def __init__(self, by_lang):
        self.by_lang = by_lang
        self.asked: list[tuple[str, int]] = []

    def sample_confidence(self, gray, boxes, languages=None):
        key = "+".join(languages or ["hi", "en"])
        self.asked.append((key, len(boxes)))
        if key not in self.by_lang:
            raise RuntimeError("no such model here")
        return self.by_lang[key]


BOXES = [[0, i * 10, 50, i * 10 + 9] for i in range(40)]


def test_a_telugu_page_picks_the_telugu_reader():
    eng = FakeEngine({"hi+en": 0.31, "te+en": 0.88, "ta+en": 0.22})
    langs, scores = choose_reader(None, BOXES, eng, candidates=[["hi", "en"], ["te", "en"], ["ta", "en"]])
    assert langs == ["te", "en"]
    assert scores["te+en"] == 0.88 and list(scores)[0] == "te+en"   # shown, not asserted


def test_a_hindi_page_keeps_the_default_reader():
    eng = FakeEngine({"hi+en": 0.87, "te+en": 0.30})
    langs, _ = choose_reader(None, BOXES, eng, candidates=[["hi", "en"], ["te", "en"]])
    assert langs == ["hi", "en"]


def test_a_close_call_does_not_reload_a_model_for_noise():
    """Swapping readers costs seconds and hundreds of megabytes. A hair's difference is not
    evidence, so the default stands."""
    eng = FakeEngine({"hi+en": 0.70, "te+en": 0.70 + MIN_GAIN / 2})
    langs, _ = choose_reader(None, BOXES, eng, candidates=[["hi", "en"], ["te", "en"]])
    assert langs == ["hi", "en"]


def test_only_a_sample_of_the_page_is_read():
    """Detection already found every box; re-reading all of them with every candidate would
    cost more than the page itself."""
    eng = FakeEngine({"hi+en": 0.5, "te+en": 0.6})
    choose_reader(None, BOXES, eng, candidates=[["hi", "en"], ["te", "en"]], sample=12)
    assert all(n <= 12 for _, n in eng.asked)


def test_a_model_that_will_not_load_is_skipped_not_fatal():
    eng = FakeEngine({"hi+en": 0.66})          # te is not installed here
    langs, scores = choose_reader(None, BOXES, eng, candidates=[["hi", "en"], ["te", "en"]])
    assert langs == ["hi", "en"] and "te+en" not in scores


def test_a_page_with_no_boxes_keeps_the_default():
    eng = FakeEngine({"hi+en": 0.9})
    langs, scores = choose_reader(None, [], eng)
    assert langs == ["hi", "en"] and scores == {} and eng.asked == []


def test_a_page_nobody_can_read_keeps_the_default():
    """Two real deeds, badly photographed: every reader scored between 0.07 and 0.34, and the
    loudest guess was Kannada - on an Andhra document. A relative lead over a field of
    failures is not evidence of a script."""
    eng = FakeEngine({"hi+en": 0.071, "te+en": 0.136, "kn+en": 0.223, "bn+en": 0.093})
    langs, scores = choose_reader(None, BOXES, eng,
                                  candidates=[["hi", "en"], ["te", "en"], ["kn", "en"], ["bn", "en"]])
    assert langs == ["hi", "en"], "a winner below the floor must not take the page"
    assert list(scores)[0] == "kn+en"      # still reported, so the near-miss is visible


def test_a_clear_winner_above_the_floor_still_takes_the_page():
    eng = FakeEngine({"hi+en": 0.164, "te+en": 0.645, "kn+en": 0.398})
    langs, _ = choose_reader(None, BOXES, eng, candidates=[["hi", "en"], ["te", "en"], ["kn", "en"]])
    assert langs == ["te", "en"]


def test_the_floor_is_absolute_not_relative():
    """A big lead over a hopeless default is still a hopeless reading."""
    eng = FakeEngine({"hi+en": 0.02, "te+en": MIN_ABSOLUTE - 0.01})
    langs, _ = choose_reader(None, BOXES, eng, candidates=[["hi", "en"], ["te", "en"]])
    assert langs == ["hi", "en"]
