# RFA Assistant

A web app that takes a patient's documents (referral letters, intake forms, clinical notes, including handwritten ones, insurance cards and lab reports) and gets a clinic to a completed **Request for Approval of Services** PDF.

- **Backend:** FastAPI (Python 3.11), PyMuPDF, Anthropic SDK
- **Frontend:** Next.js 16 (App Router), React 19, Tailwind 4

## How it works

```
upload ─► read each document ─► check it's one patient ─► merge into form fields ─► review ─► filled PDF
                (Claude)           (last name + DOB)        (with source quotes)     (edit,     (template +
                                                                                       resolve)    addendum)
```

1. **Start a request and drop in documents.** PDF, PNG or JPEG; any mix, any order.
2. **Each document is read on its own** into one schema (`DocumentExtraction`): patient, insurance, providers, diagnoses, medications, scores, requested services, symptoms, history, risk. **Every value carries the verbatim quote it came from**, plus an `uncertain` flag for hard-to-read handwriting.
   - **Claude is the only reader.** The whole PDF goes to Claude (`claude-opus-5-5`) as a document block, so it reads scans, card images and handwriting (the clinical note sample). Output is constrained with structured outputs to a flat schema (`claude/schema.py`) and converted to the internal model.
3. **Identity check.** Documents are grouped by patient (last name + date of birth). Only the selected patient's documents fill the form. The others are shown greyed out with "about a different patient". The reviewer can switch patients or force-include a document.
4. **Assembly** (`backend/app/assembly/`) builds each form field and labels where its value came from:
   | Source | Meaning |
   |---|---|
   | **From documents** | copied from a document; click it to see the page with the quote highlighted |
   | **Suggested: check** | worked out by the app (dates, CPT codes, session count, narrative draft), with a note saying how |
   | **Clinic settings** | about the clinic, not the patient (Section B) |
   | **Edited** | typed by the reviewer; never overwritten by later uploads |
   
   When documents disagree (e.g. two member IDs), the field shows *"Other documents say…"* with a one-click **Use this**.
5. **Narrative sections (E, F).** Claude drafts them once every document is read, from the extracted facts only (no names or IDs are sent in this step), and lists what a reviewer would expect but the documents don't say. They are marked *Suggested: check*. Until a draft exists, or if drafting fails, they stay empty and **Redraft with AI** tries again. Nothing else fills them.
6. **Readiness checks:** required fields, ICD-10 / CPT formats, NPI check digit, date sanity, conflicts, unread documents, signature.
7. **PDF.** The blank form has no fillable fields, so values are drawn next to the printed labels. The labels are found on the template at runtime, not hard-coded coordinates. Text that doesn't fit the ruled lines, or table rows beyond the 3 medication / 2 score rows, is cut at a clear *(continued on addendum)* marker and printed in full on an addendum page.

## Running it

Backend (port 8000):

```bash
cd backend
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
```

**Claude credentials are required.** Claude reads every document and drafts Sections E and F, and there is no other path:

- The API refuses to start without credentials. It exits with an explanation.
- Uploads are refused (503) if the credentials disappear while it runs.
- A document Claude can't read is marked *Failed*, with the reason and a Retry button. It never falls back to another reader.

The backend uses the first credential it finds, in the same order as the Anthropic SDK:

1. `ANTHROPIC_API_KEY`, from the environment or from `backend/.env` (git-ignored; see `backend/.env.example`).
2. `ANTHROPIC_AUTH_TOKEN`.
3. **A profile saved by `ant auth login`**, so no key is stored in the project. The SDK reads it from `~/.config/anthropic/` and refreshes the token itself:

   ```bash
   brew install anthropics/tap/ant
   ant auth login            # opens a browser; pick your organization and workspace
   ant auth status           # shows which credential is active
   ```

   Restart the backend afterwards. Run `ant auth login` again if the profile expires. An exported `ANTHROPIC_API_KEY` takes priority over the profile, so unset it if you want the profile to be used.

The badge in the top right shows *Claude connected* (hover for the model and credential), *Claude not connected*, or *API offline*.

Frontend (port 3100):

```bash
cd frontend
pnpm install
pnpm dev
```

Open http://localhost:3100. Set your clinic once under **Clinic settings** (facility, Tax ID, phone, fax, address, providers), then start a request.

Environment variables: `ANTHROPIC_API_KEY` / `ANTHROPIC_PROFILE` / `ANTHROPIC_CONFIG_DIR` (one credential is required, see above), `RFA_CLAUDE_MODEL` (default `claude-opus-5-5`), `RFA_DATA_DIR` (default `backend/data`), `RFA_CORS_ORIGINS`, and `NEXT_PUBLIC_API_URL` on the frontend (default `http://localhost:8000`).

Tests replay Claude's real answers for the five samples, recorded from a live run into `backend/tests/fixtures/`. They are offline and deterministic, and cover everything after the API call: credential checks, failures with no fallback, identity check, assembly, edits, validation and the PDF.

```bash
cd backend && .venv/bin/python -m pytest -q
```

Lint and format (backend, config in `backend/pyproject.toml`; install with `requirements-dev.txt`):

```bash
cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check .
```

## Deploying to Render

`render.yaml` is a Render Blueprint that creates both services:

| Service | What | Plan |
|---|---|---|
| `rfa-api` | FastAPI backend, with a 1 GB persistent disk at `/var/data` for requests and uploads | Starter (paid; disks need a paid plan) |
| `rfa-web` | Next.js frontend | Free (sleeps when idle; the first visit after that takes about a minute) |

1. Push this repository to GitHub.
2. In Render: **New → Blueprint**, pick the repository. Render reads `render.yaml` and asks for three values:
   - `ANTHROPIC_API_KEY`: an API key from the Claude Console (**Settings → API Keys**). An `ant auth login` sign-in can't be used on a server.
   - `RFA_CORS_ORIGINS`: the frontend's address, e.g. `https://rfa-web.onrender.com`.
   - `NEXT_PUBLIC_API_URL`: the backend's address, e.g. `https://rfa-api.onrender.com`.

   Render names services `<name>.onrender.com` when the name is free and adds a suffix when it isn't. If your addresses differ, update the two URLs, then redeploy `rfa-web`: the API address is built into the frontend, so it needs a new build.
3. Open the `rfa-web` address and fill in **Clinic settings** first.

Without `ANTHROPIC_API_KEY`, `rfa-api` fails to start and its log says why.

To run without paying, set `rfa-api` to `plan: free` and remove its `disk` block. Requests and uploads are then lost whenever the service restarts or redeploys.

## Assumptions

There was nobody to ask, so these are the calls I made. Each one is easy to change.

**Workflow**
- **One request = one patient and one request for services.** The sample set has five documents about five different people (Dominguez, Thompson, Nair, Rodriguez, O'Brien). I took that to mean the app must notice mismatched documents rather than merge them, not that they form one case.
- **The user is clinic staff preparing the request and the provider signs it.** The app never signs on its own. The signature line stays blank (sign the printout) unless the provider ticks an explicit attestation to apply a typed signature.
- **The output is a filled PDF to fax or upload.** Submission to a payer is out of scope.

**Where values come from**
- **Section B (requesting provider) is the clinic's data**, entered once in Clinic settings: facility, Tax ID, phone, fax, address, and providers with NPI and license number. The samples never contain the clinic's Tax ID. If a clinical note names a provider listed in settings (matched on NPI or last name), that provider is the requesting provider. If it names someone else, the document's provider is used. With no note, the default provider is used.
- **Section C is filled only when the referring provider differs from the requesting one**, as the form says ("if different").
- **Which document wins** when several give a value: insurance card → intake → referral for insurance; intake → referral → card for demographics; newest clinical note → intake → referral for clinical facts. Values from other documents that disagree are shown as alternatives, never dropped silently.
- **Payer fax** is almost never on member documents (it lives on the payer's prior-auth fax sheet). It is left empty with that hint.
- **Diagnoses on the form** are the conditions the services treat. Medical comorbidities (e.g. hypothyroidism in the referral, diabetes in the lab report) are left off the service request unless nothing else is documented.

**Inferred values (always marked *Suggested: check*)**
- **Date of request** and **signature date** = today.
- **Start date** = request date + 7 days (payer review time). The filled example's dates are 7 days apart.
- **Duration** = what the documents say (e.g. "Weekly x 12 weeks"), else 12 weeks, the length in the filled example.
- **Sessions** = frequency × weeks (Weekly → 12; 2x/week → 24), counted as psychotherapy sessions.
- **CPT codes** are suggested from the wording of the requested services: psychotherapy → 90837 (as in the example), psychiatric evaluation → 90792, medication management → 99214, intensive outpatient → S9480, group → 90853, family → 90847. These need checking against the payer's fee schedule, and the note says so.
- **Type of service** defaults to Outpatient when the documents request services without naming a level of care. "Consider IOP" in the intake form is not treated as a request for IOP.

**Quirks of the blank form**
- On the blank form, the *Payer Fax* and *Payer Phone* rows are partly covered by the Section A bar. Values there are drawn slightly higher and smaller so they stay readable.
- Values use Courier in dark blue, like the filled example. Section E/F text starts to the right of each question on the first ruled line (the example overlaps the question; this doesn't).

**AI and data**
- **Claude is mandatory.** It is the only reader and the only author of Sections E and F. A missing credential stops the server; a failed call fails that document or the draft visibly. There is no degraded mode that could quietly produce a less accurate form.
- **The narrative draft is sent facts, not identities:** age, gender, diagnoses, scores, medications, symptoms, history and risk. No name, DOB, member ID or contact details.
- **Requests opt into server-side refusal fallbacks** (`fallbacks: "default"`). If the model declines a document, the API retries on a fallback model instead of failing the upload.
- **Storage is local files** (`backend/data/`, one folder per request). There is no authentication and no encryption at rest. This is a prototype, not something to put real PHI on as is.

## What's verified and what isn't

- **Automated:** `backend/tests` (16 tests) replays Claude's recorded answers for the five samples. They cover refusing to start without credentials, failures with no fallback, patient grouping, assembly, user-edit preservation, the addendum, page highlighting and PDF layout. To refresh the fixtures after a prompt or schema change, rerun the samples through Claude and save each `DocumentExtraction` to `tests/fixtures/<sample>.extraction.json`.
- **Claude path, run on all five samples** (`claude-opus-5-5`, signed in with `ant auth login`):
  - All five documents read, about 25 s each, in parallel. The five patients were told apart, and the handwritten note's patient (James O'Brien) was chosen as primary.
  - Handwritten note: every value matched the page. That covers name, DOB 12/17/83, Anthem BCBS ID ANT-XK7829014, F33.1, Lexapro 10mg (escitalopram), PHQ-9 14 (was 21 on 1/15), Dr. R. Whitfield and NPI 1567890234. Claude also flagged the year-less "1/15" and that therapy is with a different provider (Dr. Patel).
  - Insurance card: the values that exist only as images were read (UnitedHealthcare Choice Plus PPO, UHC-84729103-05, group 742901, mental health line as payer phone).
  - Sections E and F drafted within the form's line limits, so no addendum. Claude listed 12 gaps a reviewer may ask about, e.g. no documented functional impairment, and the latest PHQ-9 being 10 months before the requested start date.
- **What the first real run caught and fixed:** the API rejected the original nested extraction schema ("compiled grammar is too large"). Claude now fills a flat schema (`backend/app/claude/schema.py`: a list of `{field, value, quote}` facts plus diagnosis, medication and score lists), converted to the same internal model. The narrative length limits were also tightened to the form's real line capacity.
- **Not measured:** accuracy beyond these five samples, or behaviour on poor-quality scans.

## What I'd do next

- Build a small labelled set of real-world documents (poor scans, faxes, multi-page notes) and measure extraction accuracy per field.
- Per-field "reviewed" ticks, and an audit log of who changed what.
- Payer directory (fax numbers, required attachments, CPT rules per payer).
- Auth, encryption at rest and a database before any real PHI.
- Attach the source documents behind the form as one fax packet.

## Layout

```
backend/
  app/
    main.py                FastAPI app: refuses to start without Claude credentials, mounts the routes
    api/
      deps.py              case/document lookup (404s) and the case view returned to the UI
      routes/              meta (health, form schema), clinic, cases, documents, form edits
    pipeline/
      processing.py        background work: Claude reads each document, then drafts Sections E/F
    claude/
      client.py            SDK client, structured-output call, error mapping
      extraction.py        extraction prompt + call
      narrative.py         narrative prompt + call
      schema.py            flat schema Claude fills, converted to the internal model
    assembly/
      assemble.py          builds the form from all documents; reviewer edits win
      identity.py          groups documents by patient (last name + DOB)
      sources.py           document priority, candidates, conflicts, evidence
      providers.py         requesting / referring provider resolution
      services.py          frequency, duration, CPT suggestions, level of care
      clinical.py          diagnoses, medications, scores, narrative facts
      validation.py        readiness checks
    documents/
      source.py            open uploads, page count, page previews with highlights
      fill.py              draw values onto the blank form, addendum
    domain/                models, form schema (every box on the form), value normalization
    core/                  config (.env loading, paths) and credential checks
    storage/store.py       one JSON file + uploads per request
  templates/               the blank Request for Approval of Services
  tests/                   end-to-end tests + fixtures/ (Claude's recorded answers)
frontend/src/
  app/                     pages: requests list, request workspace, clinic settings
  components/
    case/                  documents panel, readiness panel, source viewer
    form/                  form review, field row, tables, narrative banner, signature
    layout/                Claude connection badge
  lib/
    api/                   API types and client
    labels.ts              display labels
samples/                   the provided sample documents
render.yaml                Render Blueprint for both services
```
