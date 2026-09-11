"""Measure OCR + extraction quality on a generated split.

    python eval/evaluate.py --split test            # OCR (cached) + extraction + metrics
    python eval/evaluate.py --split dev --no-cache  # force re-running OCR

Metrics:
  * CER - character error rate of full-page OCR text vs ground truth (lower is better)
  * field accuracy - % of ground-truth fields whose extracted value is exactly right
  * review rate - % of documents routed to a human verifier
  * straight-through accuracy - of auto-accepted documents, % with every required field right
  * processing time per document
Writes eval/results/<split>.json and eval/results/<split>.md
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rapidfuzz.distance import Levenshtein  # noqa: E402

from backend.extraction.confidence import default_threshold  # noqa: E402
from backend.extraction.extractor import extract  # noqa: E402
from backend.extraction.normalize import clean, label_key  # noqa: E402
from backend.extraction.schema import FIELD_NAMES, REQUIRED_FIELDS  # noqa: E402

DATA = ROOT / "data" / "generated"
RESULTS = ROOT / "eval" / "results"


def norm_text(t: str) -> str:
    return " ".join(clean(t).split())


def cer(pred: str, gt: str) -> float:
    gt, pred = norm_text(gt), norm_text(pred)
    return Levenshtein.distance(pred, gt) / max(1, len(gt))


def field_correct(name: str, pred: dict | None, gt) -> bool:
    if pred is None or pred.get("value") is None:
        return False
    if name == "plot_area":
        n = pred.get("normalized") or {}
        return n.get("unit") == gt["unit"] and abs(float(n.get("value", -1)) - gt["value"]) < 1e-6
    if name in ("owner_name", "father_name"):
        return label_key(pred["value"]) == label_key(gt)
    return str(pred["value"]).strip().lower() == str(gt).strip().lower()


LIST_KEYS = ("owners", "parcels")
DOC_EXTS = (".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp")


def document_file(meta: dict, meta_path: Path) -> str:
    """Generated docs list their files; for real docs, the image/PDF with the JSON's name."""
    if meta.get("files"):
        return meta["files"][-1]
    for ext in DOC_EXTS:
        if meta_path.with_suffix(ext).exists():
            return meta_path.with_suffix(ext).name
    sys.exit(f"no document file next to {meta_path.name}")


def scalar_fields(meta: dict) -> dict:
    """Ground-truth single-value fields (owners/parcels lists are scored separately)."""
    return {k: v for k, v in meta["fields"].items() if k not in LIST_KEYS}


def owners_match(pred: list | None, gt: list) -> bool:
    """Every co-owner found, nothing extra (order-insensitive, normalised names)."""
    if not pred:
        return False
    return sorted(label_key(o.get("owner_name") or "") for o in pred) == sorted(label_key(o["owner_name"]) for o in gt)


def parcel_rows(pred: list | None, gt: list) -> tuple[int, int, int]:
    """(rows matched, predicted rows, ground-truth rows). A row matches when khasra,
    area value + unit and land class are all right."""
    def key(row, normalized):
        area = row.get("plot_area_normalized") if normalized else row.get("plot_area")
        area = area or {}
        return (str(row.get("khasra_number", "")).strip().lower(), area.get("unit"),
                round(float(area.get("value", -1)), 6), row.get("land_classification"))
    pred = pred or []
    left = [key(r, True) for r in pred]
    hit = 0
    for g in gt:
        k = key(g, False)
        if k in left:
            left.remove(k)
            hit += 1
    return hit, len(pred), len(gt)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--cache", default="ocr", help="OCR cache folder name (use a new one per OCR setting)")
    ap.add_argument("--out", default=None, help="results file name (default: the split name)")
    ap.add_argument("--dir", default=None, help="folder of documents + ground-truth JSON (default: data/generated/<split>); use data/real for real records")
    args = ap.parse_args()

    split_dir = Path(args.dir) if args.dir else DATA / args.split
    cache = split_dir / args.cache
    cache.mkdir(exist_ok=True)
    # generated splits name files <split>-NNN.json; real folders may use any names
    metas = sorted(split_dir.glob(f"{args.split}-*.json")) or sorted(split_dir.glob("*.json"))
    if args.limit:
        metas = metas[: args.limit]
    if not metas:
        sys.exit(f"no documents in {split_dir}; run data/generator/generate.py first")

    per_doc = []
    flag_stats: dict[str, int] = defaultdict(int)
    list_stats: dict[str, int] = defaultdict(int)
    field_hits: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    by_group: dict[str, list[float]] = defaultdict(list)
    for mp in metas:
        meta = json.loads(mp.read_text(encoding="utf-8"))
        meta.setdefault("id", mp.stem)  # real documents: the file name is the id
        cp = cache / f"{meta['id']}.json"
        if cp.exists() and not args.no_cache:
            ocr = json.loads(cp.read_text(encoding="utf-8"))
        else:
            from backend.ocr.pipeline import run_ocr

            img = split_dir / document_file(meta, mp)  # prefer the PDF when one exists
            ocr = run_ocr(img.read_bytes(), img.name)
            cp.write_text(json.dumps(ocr, ensure_ascii=False), encoding="utf-8")
        t0 = time.perf_counter()
        ext = extract(ocr)
        extract_ms = (time.perf_counter() - t0) * 1000

        text = "\n".join(l["text"] for p in ocr["pages"] for l in p["lines"])
        c = cer(text, meta["text"]) if meta.get("text") else None
        gt = scalar_fields(meta)
        correct = {}
        for name, gv in gt.items():
            ok = field_correct(name, ext["fields"].get(name), gv)
            correct[name] = ok
            field_hits[name][0] += int(ok)
            field_hits[name][1] += 1
        req_ok = all(correct.get(n, False) for n in REQUIRED_FIELDS if n in gt)
        if "owners" in meta["fields"]:
            list_stats["owner_docs"] += 1
            list_stats["owners_exact"] += int(owners_match(ext.get("owners"), meta["fields"]["owners"]))
            list_stats["multi_owner_docs"] += int(len(meta["fields"]["owners"]) > 1)
        if "parcels" in meta["fields"]:
            hit, n_pred, n_gt = parcel_rows(ext.get("parcels"), meta["fields"]["parcels"])
            list_stats["rows_hit"] += hit
            list_stats["rows_pred"] += n_pred
            list_stats["rows_gt"] += n_gt
        # human effort: which extracted fields would a verifier have to look at?
        thr = ext["threshold"]
        for name, f in ext["fields"].items():
            flagged = (not f["valid"]) or f["confidence"] < thr
            ok = name in gt and field_correct(name, f, gt[name])
            flag_stats["flagged" if flagged else "trusted"] += 1
            if not flagged:
                flag_stats["trusted_correct"] += int(ok)
        flag_stats["missing_required"] += len(ext["missing_required"])
        doc = {
            "id": meta["id"], "template": meta.get("template", "real"),
            "profile": meta.get("degradation", {}).get("profile", "real"),
            "handwritten": meta.get("handwritten", False), "cer": round(c, 4) if c is not None else None,
            "field_acc": round(sum(correct.values()) / max(1, len(correct)), 4),
            "route": ext["route"], "required_all_correct": req_ok,
            "ocr_ms": ocr["elapsed_ms"], "extract_ms": round(extract_ms, 1),
            "wrong": [n for n, ok in correct.items() if not ok],
            "reasons": ext["route_reasons"][:4],
        }
        per_doc.append(doc)
        for key in (f"template:{doc['template']}", f"profile:{doc['profile']}", f"handwritten:{doc['handwritten']}"):
            by_group[key].append(doc["field_acc"])
            if doc["cer"] is not None:
                by_group[key + ":cer"].append(doc["cer"])
        cer_txt = "  n/a" if doc["cer"] is None else f"{doc['cer']:.3f}"
        print(f"{doc['id']}  cer={cer_txt}  fields={doc['field_acc']:.2f}  {doc['route']:11s}  wrong={doc['wrong']}")

    auto = [d for d in per_doc if d["route"] == "auto_accept"]
    cers = [d["cer"] for d in per_doc if d["cer"] is not None]
    total_hit = sum(h for h, _ in field_hits.values())
    total_n = sum(n for _, n in field_hits.values())
    summary = {
        "split": args.split,
        "documents": len(per_doc),
        "cer_mean": round(statistics.mean(cers), 4) if cers else None,
        "cer_median": round(statistics.median(cers), 4) if cers else None,
        "field_accuracy": round(total_hit / max(1, total_n), 4),
        "required_field_accuracy": round(
            sum(field_hits[n][0] for n in REQUIRED_FIELDS) / max(1, sum(field_hits[n][1] for n in REQUIRED_FIELDS)), 4),
        "review_rate": round(1 - len(auto) / len(per_doc), 4),
        "straight_through_accuracy": round(sum(d["required_all_correct"] for d in auto) / len(auto), 4) if auto else None,
        "field_flag_rate": round(flag_stats["flagged"] / max(1, flag_stats["flagged"] + flag_stats["trusted"]), 4),
        "trusted_field_precision": round(flag_stats["trusted_correct"] / max(1, flag_stats["trusted"]), 4),
        "threshold": default_threshold(),
        "ocr_seconds_mean": round(statistics.mean(d["ocr_ms"] for d in per_doc) / 1000, 2),
        "owners_exact_rate": round(list_stats["owners_exact"] / list_stats["owner_docs"], 4) if list_stats["owner_docs"] else None,
        "multi_owner_docs": list_stats["multi_owner_docs"],
        "parcel_row_recall": round(list_stats["rows_hit"] / list_stats["rows_gt"], 4) if list_stats["rows_gt"] else None,
        "parcel_row_precision": round(list_stats["rows_hit"] / list_stats["rows_pred"], 4) if list_stats["rows_pred"] else None,
        "per_field": {n: {"accuracy": round(field_hits[n][0] / field_hits[n][1], 4), "n": field_hits[n][1]}
                      for n in FIELD_NAMES if field_hits[n][1]},
        "by_group": {k: round(statistics.mean(v), 4) for k, v in sorted(by_group.items())},
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = args.out or args.split
    (RESULTS / f"{out}.json").write_text(json.dumps({"summary": summary, "documents": per_doc}, ensure_ascii=False, indent=1),
                                               encoding="utf-8")
    md = [f"# Evaluation — `{args.split}` split ({summary['documents']} documents)", "",
          "| Metric | Value |", "| --- | --- |",
          (f"| CER (mean / median) | {summary['cer_mean']:.1%} / {summary['cer_median']:.1%} |" if cers
           else "| CER | n/a (no full-text transcripts) |"),
          f"| Field accuracy (all fields) | {summary['field_accuracy']:.1%} |",
          f"| Field accuracy (required fields) | {summary['required_field_accuracy']:.1%} |",
          f"| Review rate | {summary['review_rate']:.1%} |",
          f"| Straight-through accuracy (auto-accepted docs fully correct) | "
          f"{'n/a' if summary['straight_through_accuracy'] is None else format(summary['straight_through_accuracy'], '.1%')} |",
          f"| Fields flagged for a human (all extracted fields) | {summary['field_flag_rate']:.1%} |",
          f"| Precision of fields *not* flagged | {summary['trusted_field_precision']:.1%} |",
          f"| Auto-accept threshold (calibrated on dev) | {summary['threshold']} |",
          f"| OCR time per document (CPU) | {summary['ocr_seconds_mean']} s |", ""]
    if summary["owners_exact_rate"] is not None:
        md[-1:-1] = [f"| All co-owners found ({summary['multi_owner_docs']} multi-owner docs) | {summary['owners_exact_rate']:.1%} |"]
    if summary["parcel_row_recall"] is not None:
        md[-1:-1] = [f"| Parcel rows recovered (recall / precision) | {summary['parcel_row_recall']:.1%} / {summary['parcel_row_precision']:.1%} |"]
    md += [
          "## Per field", "", "| Field | Accuracy | n |", "| --- | --- | --- |"]
    md += [f"| {n} | {v['accuracy']:.1%} | {v['n']} |" for n, v in summary["per_field"].items()]
    md += ["", "## By document group (field accuracy / CER)", "", "| Group | Field acc. | CER |", "| --- | --- | --- |"]
    groups = summary["by_group"]
    md += [f"| {k} | {v:.1%} | " + (f"{groups[k + ':cer']:.1%}" if k + ":cer" in groups else "n/a") + " |"
           for k, v in groups.items() if not k.endswith(":cer")]
    (RESULTS / f"{out}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("per_field", "by_group")}, indent=1))


if __name__ == "__main__":
    main()
