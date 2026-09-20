"""Choosing the reader by reading a little of the page with each candidate."""
from backend.ocr.scripts import MIN_GAIN, choose_reader


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
