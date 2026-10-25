# Test results and verification status

Authoring environment: Linux, Python 3.13, with `pydantic 2.13`, `Pillow 12.3`, `requests 2.34`, `pandas 3.0`.
**`streamlit`, `anthropic` and `pytest` could not be installed there (package index blocked by the sandbox), and
Anthropic / Open-Meteo were unreachable.** Results below are split accordingly. Re-run everything on your machine
with the commands in the last section.

## ✅ Executed and passing (52 tests, `python -m unittest discover -s tests -t . -v`)

| Module | Tests | What is covered |
|---|---|---|
| `test_schemas` | 7 | enum normalisation, extra-field tolerance, invalid values rejected, valuation ordering, plan cycle / unknown-dependency / duplicate-id / empty / duration checks |
| `test_llm` | 8 | JSON extraction (plain, fenced, in prose, none), compact schema hint, no-key → `LLMUnavailable`, image block format, repair-retry success, give-up after retry, transport errors propagate (**fake transport, not the real API**) |
| `test_imaging` | 6 | PNG→JPEG, downscaling, RGBA flattening, empty / garbage / tiny / oversize rejected, 4-image cap with error list |
| `test_estimator` | 8 | unit conversion, thumb-rule maths, wastage, input validation, M20 concrete and brickwork maths, cost summary, benchmark cost, cost-approach baseline, crack-width categories |
| `test_scheduler` | 6 | critical path and slack, Sunday skipping, weekend start roll-forward, holidays, all validation errors, template validity and scaling |
| `test_weather` | 11 | rule thresholds (rain, wind, storm, heat, cold), missing data never restricts, forecast text, geocode / forecast parsing (**mocked HTTP**), friendly errors on network failure, bad status and bad JSON |
| `test_projectdata` | 6 | profile round-trip and validation, CSV truncation, JSON summary, error cases, latin-1 CSV, secret lookup |

## 🟡 Executed with a stand-in (not real Streamlit)

A throwaway harness (not shipped) ran `app.py` and every tab against a **stub `streamlit` module** with a scripted
fake LLM transport and mocked HTTP:

- no API key, nothing clicked: renders all 9 tabs, shows the "AI not configured" notice, no tab errors;
- fake key, every action button clicked with uploads: all 9 result objects were produced and rendered, no errors.

This catches NameErrors/typos in UI code paths. It does **not** prove real Streamlit accepts every call or that the
layout looks right.

## ⛔ Not verified (could not run in the authoring environment)

| Item | Status |
|---|---|
| `streamlit run app.py` real startup, layout, widget behaviour | **Not run.** `tests/test_app_streamlit.py` (real `AppTest`) is included but was skipped |
| Live Anthropic calls (accuracy of safety / crack / valuation output, model access for `claude-sonnet-5-5`, SDK call shape) | **Not run** |
| Live Open-Meteo geocoding and forecast | **Not run** (parsing verified against a mocked payload shaped like the documented API) |
| Python 3.9 / 3.10 / 3.11 / 3.12 runtime | **Not run.** All files parse with `ast.parse(feature_version=(3, 9))`; code avoids `X | Y` annotations and `match` |
| Streamlit Community Cloud deployment | **Not done** |
| React / Vite build | N/A: there is no React frontend |
| Demo video | **Not created**; script and checklist are in `docs/VIDEO_DEMO.md` |
| `.gitignore` | Verified in a throwaway git repo: `.streamlit/secrets.toml`, `.env`, `.venv/` are ignored; no key-like strings besides placeholders |

## Re-run on your machine

```bash
pip install -r requirements-dev.txt
python -m unittest discover -s tests -t . -v     # expect 53 tests, 0 skipped once Streamlit is installed
pytest -q                                        # same tests via pytest
streamlit run app.py                             # then click through each tab; see docs/VIDEO_DEMO.md for sample inputs
```

First live smoke test (≈2 minutes, uses a few cents of API credit): set `ANTHROPIC_API_KEY`, upload
`sample_data/images/synthetic_site_workers.png` in **Safety** and press *Analyze safety*; fetch a forecast in **Weather**.
If the model name is rejected, set `ANTHROPIC_MODEL` to a model your account can use.
