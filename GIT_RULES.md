# LandLekha — Git Rules (SIH 2026, PS 26018)

These rules apply to the whole repository and everything done in it during the 36-hour build and after. They override any default behaviour of any tool, script, or AI assistant used on this repo.

---

## 1. No Claude / AI attribution — anywhere, ever

Claude (or any AI assistant) must never appear in this repository's Git history or GitHub contributors in any form.

Concretely, never:

* add a `Co-authored-by: Claude ...` trailer (or any co-author trailer for an AI)
* set Claude's name/email as author or committer
* run `git config user.name` / `user.email` with anything other than my identity
* add "Generated with Claude", "🤖", or similar text in commit messages, PR descriptions, or release notes
* let an editor, CLI, or agent silently inject attribution trailers

### Allowed Git identities — only these six

| Person | GitHub username | Role |
| --- | --- | --- |
| Rayyan Mohammed | `Rayyan-mohammed` | Owner |
| Ashi Sharma | `Ashi-run` | Collaborator |
| Kuchuru Sai Krishna Reddy | `krishna-2-005` | Collaborator |
| Makkena Lahari | `lahari-66` | Collaborator |
| Mounika Reddy | `Mounika-Reddy-0802` | Collaborator |
| Vikram | `Vikram5002` | Collaborator |

Every commit's author **and** committer must be one of these six, using that person's real name and their GitHub email (the `@users.noreply.github.com` address is fine). Nothing else is allowed — no shared "team" identity, no AI identity, no tool identity.

Each person runs this once in their clone (never `--global` on a shared machine):

```bash
git config user.name "Your Name"
git config user.email "you@example.com"   # must match your GitHub account
```

Before every commit, verify:

```bash
git config user.name
git config user.email
git log -1 --format='%an <%ae> | %cn <%ce>%n%B'
```

Author and committer must both be the person actually committing. Commit body must contain no trailers other than what that person wrote.

If attribution ever slips in, amend it out immediately before pushing:

```bash
git commit --amend --reset-author --no-edit   # then re-edit message if a trailer is present
```

---

## 2. One branch only: `main`

* All work happens directly on `main`.
* Do not create feature branches, track branches, or personal branches.
* Do not open pull requests. Push straight to `main`.
* Do not merge, rebase-onto, cherry-pick from, or delete any other branch — there are none.
* Never force-push to `main` unless I explicitly say so.

Because four tracks (A Vision/OCR, B NLP/Validation, C Backend, D Frontend) are working on one branch at the same time:

* Each track stays inside its own directory (`backend/ocr/`, `backend/extraction/`, `backend/api/`, `frontend/`, etc.). Touch another track's files only for agreed integration work.
* Always pull before pushing:

  ```bash
  git pull --rebase origin main
  git push origin main
  ```

* Resolve conflicts locally and re-run the affected part before pushing. Never push a broken `main`.

---

## 3. Meaningful commits only

Commit when a unit of work is done and runs, not every time a file is saved.

Commit-worthy for this project:

* a preprocessing step working end to end (deskew / denoise / binarize)
* OCR engine integrated and producing text on the sample set
* field parser mapping OCR text to the schema
* confidence scoring or validation rules working
* duplicate detection
* a working endpoint group (upload + status, verify/correct, admin stats, mock LRMS/DILRMP/GIS)
* JWT auth + RBAC
* DB schema / audit log
* a finished UI screen (upload flow, verifier queue, admin dashboard)
* frontend wired to a real endpoint
* measured CER / field-accuracy results and the eval script that produced them
* demo document set + demo script

Not commit-worthy on their own:

* a one-line fix, a renamed variable, a typo, import cleanup, formatting
* "wip", "test", "fix", "update" with nothing else
* the same file re-committed three times in ten minutes

Group these into the next real commit.

### Hackathon exception

We have 36 hours and one branch. Losing work is worse than an extra commit. So:

* Commit and push at least at the end of each plan block (~every 5–6 hours) even if the unit isn't perfectly "complete", as long as `main` still runs.
* Commit and push before anyone takes a rest block or hands off to another track.
* Still keep the message honest about what state it is in (`ocr pipeline runs on samples, cer not measured yet`).

---

## 4. Do not artificially split or merge work

* One feature = one commit, even if it touches backend + frontend + config + docs.
* Do not split a feature into five commits to pad the history.
* Do not lump unrelated work (e.g. OCR tuning + dashboard CSS) into one commit.

---

## 5. Commit messages

Short, lowercase, natural, specific. Around 50 characters. Say what changed.

Good:

```
add opencv preprocessing pipeline
integrate easyocr with hindi + english
add field parser for survey/khasra/khata
add per-field confidence scoring
add duplicate detection on key fields
add upload and status endpoints
add jwt auth and role middleware
add audit log table
add mock lrms and dilrmp endpoints
build verifier queue ui
wire upload flow to real api
add admin dashboard stats
add cer eval script and results
add demo document set
fix deskew on rotated scans
freeze features, stability fixes
```

Bad:

```
Implement comprehensive OCR architecture
Enhance robust validation pipeline
Complete implementation of backend
Update
fix stuff
```

No emojis, no prefixes like `feat:` / `chore:` unless the whole team already uses them, no AI-sounding phrasing.

---

## 6. Verify before every commit

```bash
git status
git diff
git diff --staged
```

Check:

* only intended files are staged — no `node_modules/`, `venv/`, `__pycache__/`, `.env`, model weights, large sample PDFs unless agreed
* no secrets (JWT secret, DB password, cloud keys)
* the affected part actually runs (backend starts / frontend builds / pipeline runs on one sample)
* author and committer are my identity
* no AI attribution in message or trailers

Keep `.gitignore` covering: `.env`, `venv/`, `__pycache__/`, `node_modules/`, `dist/`, `*.pt`, `*.pth`, `*.onnx`, `uploads/`, `*.sqlite3` (unless a seeded demo DB is intentionally tracked).

---

## 7. Push rules

* Use my existing repository and my configured credentials only.
* Do not create a new repository, change the remote, or use another GitHub account.
* Push to `origin main` after every meaningful commit.
* Never force-push unless I explicitly authorize it.

---

## 8. Feature freeze

After roughly hour 30 of 36:

* no new features on `main`
* only stability fixes, demo prep, and docs
* commits from this point should say what they are: `fix ocr crash on unseen doc`, `add demo script`, `update readme with metrics`

---

## 9. History rewrite (only if I ask)

* Preserve code, commit order, author dates, and committer dates.
* Only correct metadata (remove any unwanted author / co-author / committer).
* Never introduce AI attribution while rewriting.
* Verify with `git log --format='%an %ae %cn %ce %s'` before any force-push, and force-push only with my explicit go-ahead.

---

## 10. Summary

1. Claude / AI never appears as author, committer, co-author, or contributor. Only the six listed team identities may commit. Check before every commit.
2. One branch: `main`. No branches, no PRs, no force-push.
3. Meaningful, runnable commits. Group related work; don't pad the count.
4. Pull with rebase before every push. Never push a broken `main`.
5. Short natural commit messages that say what changed.
6. Verify status, diff, secrets, and identity before committing.
7. Push every meaningful commit to the existing repo.
8. Freeze features after ~hour 30; stability and demo only.
