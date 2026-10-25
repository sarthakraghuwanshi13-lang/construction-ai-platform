# Final submission checklist

Items marked **(you)** were not and could not be done by the assistant that prepared this repository.

## Code and repository
- [x] `app.py`, `requirements.txt`, `.gitignore`, `README.md`, `.streamlit/config.toml`, source, tests, sample data present
- [x] `.gitignore` verified: `.streamlit/secrets.toml`, `.env`, `.venv/`, caches are not tracked
- [x] No API keys in the repository (only the placeholder `sk-ant-your-key-here`)
- [ ] **(you)** `pip install -r requirements-dev.txt` then `python -m unittest discover -s tests -t . -v` → all 53 pass, none skipped
- [ ] **(you)** `streamlit run app.py` locally; click every tab once with a real key
- [ ] **(you)** Replace `<your-user>/<your-repo>` placeholders in the README with your real GitHub URL
- [ ] **(you)** `git init … git push -u origin main` (exact commands in the README)
- [ ] **(you)** Pick and add a `LICENSE` file if the submission requires one
- [ ] **(you)** Repository is visible to the reviewers (public, or access granted)

## Deployment
- [ ] **(you)** Streamlit Community Cloud app created: repo, branch `main`, file `app.py`, Python 3.11/3.12
- [ ] **(you)** Secret `ANTHROPIC_API_KEY` added in *App settings → Secrets*; spending limit set in the Anthropic console
- [ ] **(you)** Deployed URL opens in a private/incognito window; AI sidebar shows "AI enabled"
- [ ] **(you)** One successful run of each AI tab and the weather tab on the deployed app
- [ ] **(you)** Deployed URL added to the README and the submission form

## Video (2–3 minutes)
- [ ] **(you)** Recorded following `docs/VIDEO_DEMO.md`; shows the deployed URL, all nine capabilities, limitations
- [ ] **(you)** Real or openly licensed photos used (or synthetic ones labelled as synthetic)
- [ ] **(you)** Uploaded (YouTube unlisted / Drive / LMS) and the link tested while logged out

## Documentation to include or cite
- [x] Architecture and mapping to the reference diagram (README)
- [x] Testing results and what was *not* verified (`docs/TEST_RESULTS.md`)
- [x] Known limitations (README)
- [ ] **(you)** If your criteria require a React + FastAPI split, tell the assistant: that variant is not built here

## Last look
- [ ] **(you)** Searched the repo for personal data (names, emails, phone numbers) you do not want public
- [ ] **(you)** Screenshot of each tab saved as backup evidence
