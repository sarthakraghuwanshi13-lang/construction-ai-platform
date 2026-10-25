# 🏗️ AI-Powered Multimodal Construction Intelligence Platform

A Streamlit app that combines a multimodal LLM (Anthropic Claude: text + images) with deterministic
construction calculators. It covers site safety/PPE analysis, crack assessment, valuation, material
estimation and costing, project scheduling, a daily site assistant, weather-aware advisories and a
construction knowledge assistant. Every AI reply is **validated against a Pydantic schema** before it is shown.

> **Honesty notes.** No object-detection model is bundled; image findings come from a vision-language model's
> description and can be wrong. AI features are disabled (and clearly labelled) when no API key is set;
> the app never fabricates AI output. Valuation has no live market data. Cost rates are placeholders.
> Nothing here replaces a safety officer, structural engineer or licensed valuer.

## Features

| Tab | What it does | Engine |
|---|---|---|
| 🦺 Safety | PPE check (hard hat, vest, boots, gloves, eye protection, harness), hazards, risk level, immediate actions | AI (vision) |
| 🧱 Cracks | Crack type, severity, probable causes, corrective actions, monitoring, "engineer needed" flag; optional measured-width cross-check (BRE Digest 251 style categories) | AI (vision) + rules |
| 🏠 Valuation | Low/mid/high value range with factors and assumptions; optional local cost-approach baseline | AI + rules |
| 🧮 Estimator | Materials from thumb rules, cost summary (labour, contingency), benchmark cost per sq ft, concrete and brickwork calculators; editable rates; CSV export | Rules (no AI) |
| 📅 Planning | Task plan from AI or a generic template; working-day calendar, critical path, slack, Gantt chart, CSV export | AI tasks + code scheduling |
| 📝 Daily | Notes (+ photos) → structured daily report, action items, next-day plan | AI |
| 🌦️ Weather | Live forecast (Open-Meteo, no key), go / caution / no-go per activity, optional AI narrative | API + rules (+ AI) |
| 📚 Knowledge | Construction Q&A with key points and standards to verify | AI |
| 🔎 Analyzer | Free-form analysis of images and/or a CSV/JSON project file → JSON | AI (vision) |

Sidebar: project profile (import/export JSON), optional CSV/JSON project data used as context, API status.

## Architecture

```
Browser ── Streamlit UI (app.py, construction_ai/ui/*)
              │
              ├─ construction_ai/imaging.py     validate, orient, downscale images (max 4, 1568 px)
              ├─ construction_ai/llm.py         Anthropic Messages API, JSON extraction, schema validation, 1 repair retry
              ├─ construction_ai/schemas.py     Pydantic response models (+ plan graph validation)
              ├─ construction_ai/estimator.py   thumb rules, concrete/brickwork maths, cost summary, valuation baseline
              ├─ construction_ai/scheduler.py   working-day scheduling, critical path, template plan
              ├─ construction_ai/weather.py     Open-Meteo client + rule-based site assessment
              └─ construction_ai/projectdata.py profile + CSV/JSON project-data summaries
```

**How this maps to the reference diagram.** React frontend → Streamlit; FastAPI backend → in-process Python
modules in `construction_ai/` (a separate API server adds deployment cost without benefit here); data storage →
session state plus JSON/CSV export (Streamlit Cloud's disk is ephemeral, so nothing is persisted server-side).
If your project criteria *require* a React + FastAPI split, that is **not implemented**; `construction_ai/` has no
Streamlit dependency outside `ui/`, so it can be wrapped by FastAPI, but that would be a separate frontend/backend
deployment.

**Token-saving choices:** images downscaled and capped at 4, `max_tokens` 1600 (3000 for plans), compact JSON
schema in the prompt, one repair retry only, no chat history, uploaded data truncated to 2,500 characters,
calculators/scheduling/weather rules run locally without the model.

## Quick start (local)

Requires Python 3.9+ (3.11 or 3.12 recommended).

```bash
git clone https://github.com/<your-user>/<your-repo>.git
cd <your-repo>
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Provide your key (pick one)
export ANTHROPIC_API_KEY="sk-ant-..."            # Windows PowerShell: $env:ANTHROPIC_API_KEY="sk-ant-..."
# or: cp .streamlit/secrets.toml.example .streamlit/secrets.toml   and edit it (git-ignored)

streamlit run app.py
```

Without a key the app still runs; the estimator, scheduler template and weather rules work, and AI tabs show a
"not configured" notice. Optional: `ANTHROPIC_MODEL` overrides the default model (`claude-sonnet-5-5`).

## Tests

```bash
python -m unittest discover -s tests -t . -v      # stdlib runner, no extra packages
# or, after: pip install -r requirements-dev.txt
pytest -q
```

Unit tests use a fake LLM transport and mocked HTTP, so they need no key or network.
`tests/test_app_streamlit.py` starts the real app with Streamlit's `AppTest` and is skipped if Streamlit is not
installed. See [`docs/TEST_RESULTS.md`](docs/TEST_RESULTS.md) for what was and was not verified.

## Push to GitHub

1. Create an empty repository on github.com (no README/licence/.gitignore; this repo has them), e.g. `construction-intelligence`.
2. From the project folder:

```bash
git init
git add .
git status                      # confirm .streamlit/secrets.toml, .env and .venv are NOT listed
git commit -m "Initial commit: Construction Intelligence Platform"
git branch -M main
git remote add origin https://github.com/<your-user>/<your-repo>.git
git push -u origin main
```

If prompted for a password, use a GitHub Personal Access Token (or `gh auth login`). If you ever commit a key by
mistake, **revoke it in the Anthropic console immediately**; deleting the file later does not remove it from history.

## Deploy on Streamlit Community Cloud

1. Push the repository to GitHub (public, or private with Streamlit access granted).
2. Go to <https://share.streamlit.io>, sign in with GitHub and choose **Create app / New app**.
3. Select your repository, branch `main`, and main file path `app.py`.
4. Open **Advanced settings**: choose Python 3.11 or 3.12 and paste your secrets (TOML):

   ```toml
   ANTHROPIC_API_KEY = "sk-ant-your-key-here"
   # ANTHROPIC_MODEL = "claude-sonnet-5-5"
   ```
5. Click **Deploy**. Changing secrets later: *App settings → Secrets*. Pushing to `main` redeploys automatically.

**Required secrets:** `ANTHROPIC_API_KEY` (only for AI tabs). Weather needs no key. A public deployment spends
*your* API credit on every AI click, so set a spending limit in the Anthropic console or keep the app private.

## Project layout

```
app.py                    entry point (streamlit run app.py)
construction_ai/          core logic + ui/ tab renderers
tests/                    unittest-style tests (pytest-compatible)
sample_data/              profile, BOQ CSV, site notes, synthetic test images
scripts/make_sample_images.py
docs/                     VIDEO_DEMO.md, SUBMISSION_CHECKLIST.md, TEST_RESULTS.md
.streamlit/               config.toml, secrets.toml.example
```

## Known limitations

- Vision analysis is descriptive, not measurement: crack width needs a scale reference or your own measurement.
- AI output is schema-valid, not guaranteed correct. A malformed reply gets one automatic repair attempt, then an error.
- Valuation has no comparable-sales data; estimator thumb rules and default INR rates are indicative placeholders.
- Weather thresholds are generic rules of thumb; equipment limits (e.g. crane wind limits) must come from the manufacturer.
- Session state is per browser tab; export profile/schedule/JSON to keep results.
- Images are sent to the Anthropic API for analysis. Do not upload anything you are not permitted to share.
- Streamlit Community Cloud apps sleep when idle and the first request after waking is slow.
- Sample images in `sample_data/images/` are **synthetic drawings** for pipeline testing, not real photographs.

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Your credit balance is too low" / "credits depleted" | Your Anthropic account has $0 balance. Purchase credits ($5 min) at [Anthropic Plans & Billing](https://console.anthropic.com/settings/plans), or switch to **Google Gemini (free)** in the sidebar, or enable **Demo Mode**. |
| "AI analysis is not configured" | Set `ANTHROPIC_API_KEY` or `GEMINI_API_KEY` (env var, Streamlit Secrets, or sidebar field), or switch to **Demo Mode**. |
| "Authentication failed" | Key is wrong/revoked, or the account lacks access to the chosen model; set `ANTHROPIC_MODEL` or check key. |
| "reply did not match the expected format" | Retry; if repeated, use a clearer photo or shorter notes. |
| Weather: "service unreachable" | Network blocks `open-meteo.com`; the rest of the app is unaffected. |

