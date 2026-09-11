# Working in parallel on 3 laptops

One branch (`main`), three laptops, and **each laptop owns its folders**. Two laptops
must never edit the same file in the same work block. That's what keeps
`git pull --rebase` conflict-free and lets all three move at full speed.

## Who owns what

| Laptop | Track | Owns (only this laptop edits) |
| --- | --- | --- |
| **L1** (the current laptop) | A — Vision / OCR + measurements | `backend/ocr/`, `eval/`, `backend/extraction/master/calibration.json` |
| **L2** | B + C — Extraction + backend | `backend/extraction/` (except calibration.json), `backend/api/`, `data/generator/`, `tests/` |
| **L3** | D — Frontend + demo + real data | `frontend/`, `docs/` (except contracts.md), `data/demo/`, `data/real/` |

Shared files: change them only after telling the group, in a small separate commit, then push straight away.
- `docs/contracts.md`, `backend/extraction/schema.py`, `frontend/src/constants.js` (mirrors the schema)
- `README.md`, `backend/requirements.txt`, `frontend/package.json`

## Task board (top = do first)

### L1 — OCR accuracy and speed
1. **Phone photos (58.6%, weakest case).** Try 2x upscaling of soft pages before text detection. A/B it with `eval/compare.py` exactly as in `eval/results/experiments.md`, and adopt it only if field accuracy rises.
2. **Khatauni tables (70.5%).** Detect the table grid with OpenCV (horizontal and vertical line morphology) and OCR each cell separately, so values stop merging or dropping their dots.
3. **Speed.** If any team member has an NVIDIA GPU laptop, run the demo on it (EasyOCR switches to GPU automatically: about 1–2 s per page).
4. At the end of every block: `python eval/calibrate.py --split dev` then `python eval/evaluate.py --split test`, and commit `eval/results` together with `calibration.json`.

### L2 — Realistic records
1. **Multiple owners and multiple khasra rows per khata.** Real Khataunis list several co-owners and several parcel rows (khasra, area, class) under one khata. Today every field holds one value. Plan:
   - extend the schema with `owners: []` and `parcels: []`;
   - update `docs/contracts.md` **first** and tell L3;
   - add the matching DB tables, API responses and LRMS format.
2. **Generator:** add a multi-row Khatauni template and a typewriter-style Hindi template, so item 1 can be measured.
3. **Master data:** load the official LGD village list for UP, MP, RJ and BR into `master/`, replacing the sample villages.
4. **Deployment:** `docker-compose.yml` (Postgres + API + built UI), then a cloud VM, so the judges get a live URL.

### L3 — What the judges see
1. **Real documents (highest credibility gain).** Collect 20–30 real land-record images: public Bhulekh / Khatauni printouts, or team members' family documents with permission, with personal details blacked out.
   - Put them in `data/real/` with a `<name>.json` of correct field values, in the same format as `data/generated/*/*.json` (a `text` field is not needed).
   - Ask L1 to run the evaluation on them.
2. **Hindi / English UI toggle**, since officials and citizens read Hindi.
3. **Multi-owner / multi-parcel display**, once L2 has published the contract change.
4. **Pitch deck, 2-minute demo video, rehearsal** with `docs/demo-script.md`, including one unseen document.

## Setting up L2 and L3 (about 20 minutes, not 2 hours)

1. Install **Python 3.11+** (tick "Add to PATH"), **Node.js 18+** and **Git**.
2. Clone **outside OneDrive** (OneDrive sync made OCR about 2x slower on L1):
   `git clone https://github.com/Rayyan-mohammed/Land-Lekha.git C:\dev\Land-Lekha`
3. Copy `landlekha-bundle.zip` from L1 (pendrive or Google Drive). It holds the OCR models plus the dataset with cached OCR.
4. Run the setup, with **your own** name and GitHub email:

   ```powershell
   cd C:\dev\Land-Lekha
   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Name "Your Name" -Email "ID+username@users.noreply.github.com" -Bundle "D:\landlekha-bundle.zip"
   ```

   Your noreply address is on github.com → Settings → Emails. It is also `https://api.github.com/users/<username>`'s `id` + `+<username>@users.noreply.github.com`.
5. Run `scripts\start.ps1` and open http://localhost:5173.

## Daily routine (every laptop)

```bash
git pull --rebase origin main          # before starting a task
# ... work only in your folders ...
python -m pytest tests -q              # must pass
git status && git diff --staged        # only your files, no secrets / data / node_modules
git commit -m "short lowercase message"
git pull --rebase origin main && git push origin main
```

- Push at the end of every finished task, at least every 2–3 hours, and before any break.
- Never force-push. If a pull hits a conflict in a file you don't own, stop and ask its owner.
- Post each push in the group chat in one line: *"L2 pushed: multi-owner schema — L3 can start the owners UI"*.

## Hand-offs between laptops

| When | From → to | What |
| --- | --- | --- |
| L2 changes the schema | L2 → L3, L1 | update `docs/contracts.md` + `schema.py` in one commit, then post in the chat |
| L3 adds real documents | L3 → L1 | `data/real/` pushed; L1 runs the evaluation and commits the numbers |
| L1 changes OCR | L1 → all | only after an A/B win; new numbers go in `eval/results/` |
| Before demo day | everyone → L3 | feature freeze; L3 rehearses on the final `main` |
