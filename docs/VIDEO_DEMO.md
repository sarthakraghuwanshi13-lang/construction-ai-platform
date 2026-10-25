# Video demonstration kit (target length 2:50, limit 3:00)

No video was recorded or generated; this file is the script, sample inputs, expected outputs and checklists to record it.
**Do not read AI output aloud before you see it on screen**; AI wording varies run to run. The numbers marked
✔ deterministic below come from rule-based code and will always match.

## 0. Before recording

- [ ] `ANTHROPIC_API_KEY` set via env var or Streamlit Secrets (not typed on camera; the sidebar field is masked but avoid it)
- [ ] App deployed; open the **deployed URL** in a clean browser window (address bar visible at least once)
- [ ] Sidebar → *Import profile* → `sample_data/project_profile.json` (Bhopal, 1,500 sq ft, 2 floors, INR)
- [ ] Photos ready: a **real** site photo with workers (your own, or an openly licensed one: Pexels / Unsplash / Wikimedia Commons; check the licence) and a real wall-crack close-up, ideally with a ruler or coin. `sample_data/images/synthetic_*.png` are crude drawings for testing the upload pipeline only. If you show them, say they are synthetic.
- [ ] Dry run every AI step once (AI calls take a few seconds; plan to cut or speed up the waiting)
- [ ] Do a final check that no personal data, API keys or private project photos are visible

## 1. Timed script

| Time | Screen | Narration |
|---|---|---|
| 0:00–0:15 | Deployed app, title and 9 tabs | "This is the Multimodal Construction Intelligence Platform: one app where site photos, project data and plain-language questions turn into structured, validated analysis for safety, quality, cost and planning." |
| 0:15–0:30 | Sidebar *About & limitations*, then README architecture block | "It's built with Streamlit and Python, with Claude's vision-language API as the AI engine. Every AI answer is checked against a schema. Cost, scheduling and weather rules run as plain code, so they never depend on the model." |
| 0:30–0:50 | **Safety** tab: upload site photo → *Analyze safety* | "Safety: I upload a site photo. The model returns an overall risk level, a PPE checklist, specific hazards, and immediate actions. It marks PPE as 'unclear' when it can't tell, rather than guessing." |
| 0:50–1:10 | **Cracks** tab: upload crack photo, element *Brick/block wall*, tick *I measured width*, 0.5 mm → *Assess crack* | "Cracks: the model classifies the crack, rates severity, lists probable causes and corrective actions, and says if an engineer is needed. Because I entered a measured width, a rule-based check shows the damage category next to the AI's opinion." |
| 1:10–1:30 | **Estimator** tab (profile area 1,500 sq ft) | "Estimation is fully rule-based and editable. For 1,500 square feet it computes quantities with wastage, labour and contingency, and exports to CSV. There are also concrete and brickwork calculators." |
| 1:30–1:45 | **Valuation** tab: values below → *Estimate value with AI* | "Valuation combines a local cost-approach baseline with an AI market range, with its assumptions and a clear note that there's no live comparable data." |
| 1:45–2:05 | **Planning** tab: *Use generic template*, then *Generate plan with AI* | "Planning: tasks come from the AI or a template, but dates, the working-day calendar and the critical path are computed in code. The Gantt chart highlights what drives the finish date." |
| 2:05–2:25 | **Weather** tab: Bhopal → *Fetch forecast*; then **Daily** tab: paste notes → *Generate daily report* | "Weather uses a live forecast and marks each activity go, caution, or no-go. The daily assistant turns rough notes, with the weather included, into a structured report with action items." |
| 2:25–2:40 | **Knowledge** tab question; **Analyzer** tab with `boq_sample.csv` → expand *Structured JSON response* | "A knowledge assistant answers practical questions and flags standards to verify. The analyzer accepts images and project data, and every result is available as validated JSON." |
| 2:40–2:55 | Back to title or README limitations | "To summarise: nine capabilities, schema-validated AI output, and honest labelling when AI is unavailable. It assists professionals, and doesn't replace safety officers, engineers or valuers. Thanks for watching." |

## 2. Sample inputs and expected outputs

### Safety
- **Input:** a site photo; optional notes `3 workers, first-floor slab edge`.
- **Expect (layout):** metrics *Overall risk* and *People visible*; summary; PPE table (item / status / note); expandable hazards with severity and recommendation; *Immediate actions*; limitations caption; *Structured JSON* expander + download.
- **Check:** statuses are only `present`, `missing` or `unclear`. For `synthetic_site_workers.png` a vision model *should* notice that one figure has no hard hat (not guaranteed; it's a crude drawing).

### Cracks
- **Input:** crack photo; element *Brick/block wall*; location `east wall near window`; measured width **0.5 mm**.
- ✔ **Deterministic:** the blue box shows **Category 1: Very slight**, "Cosmetic; fill during routine decoration." (use 3 mm → Category 2 *Slight*; 10 mm → Category 3 *Moderate*).
- **Expect (AI):** severity metric, engineer-needed metric, confidence, type, rationale, causes, actions, monitoring advice.

### Estimator (area 1,500 sq ft, wastage 5 %, labour 50 %, contingency 5 %)
✔ **Deterministic expected values:**

| Item | Quantity | Amount (INR) |
|---|---|---|
| Cement | 630 bags | 252,000.00 |
| Steel (TMT) | 6,300 kg | 409,500.00 |
| Sand | 1,890 cft | 103,950.00 |
| Coarse aggregate | 2,126.25 cft | 95,681.25 |

Metrics (shown rounded): Materials **INR 861,131**, Labour & other **INR 430,566**, Total incl. contingency **INR 1,356,282**.
Benchmark expander, *Standard*: **INR 2,850,000**. Concrete calculator 10 m³ M20: **80.6 bags**, sand **4.20 m³**, aggregate **8.40 m³**.
Brickwork 20 m × 3 m × 230 mm, 10 % openings: **12.42 m³ → 6,521 bricks**, **15.7 bags** cement, **3.26 m³** sand.

### Valuation
- **Input:** Independent house; location `Bhopal`; land 1,200 sq ft; built-up 1,500; age 5; 3 bedrooms; *Good*; currency INR; in the expander: land rate **5,000**, construction rate **2,000**.
- ✔ **Deterministic baseline box:** *Land INR 6,000,000 + building INR 2,750,000 (after 8.3 % depreciation) = INR 8,750,000*.
- **Expect (AI):** Low / Mid / High metrics with Low ≤ Mid ≤ High, factors table, assumptions listing the lack of live comparables, disclaimer.

### Planning (template)
- **Input:** start **Mon 2 Nov 2026**, floors 2, area 1,500 sq ft, Sunday off, press *Use generic template (no AI)*.
- ✔ **Deterministic:** 16 tasks, **12 critical**, finish **19 Mar 2027** (no public holidays modelled). Source metric reads *Template (not AI)*.
- AI plan: expect 12–30 tasks; the app rejects cyclic or unknown dependencies and shows an error instead of a plan.

### Weather (live)
- **Input:** `Bhopal`, 7 days. **Expect:** a 7-row forecast table, a go / caution / no-go grid for six activities, per-day notes; values depend on the live forecast, so don't pre-script them. Needs internet access to `open-meteo.com`.

### Daily assistant
- **Input:** paste the three sections of `sample_data/site_notes_sample.txt` into *Crew*, *Work done*, *Issues*.
- **Expect:** summary, completed work, issues (should include the late cement and the missing harness), plan for tomorrow, action items with priority.

### Knowledge
- **Input:** `What is the minimum curing period for OPC concrete and why does it matter?`
- **Expect:** answer, key points, *Standards to check* (verify the edition), follow-up questions, confidence.

### Analyzer
- **Input:** upload `sample_data/boq_sample.csv`; instructions `Which materials are under-ordered compared with the plan?`
- **Check:** the data is shown in *Data sent to the model*. The answer *should* say all five items have ordered quantity below planned quantity (e.g. cement 400 vs 630); if it does not, say so in the video rather than editing it out.

## 3. Screen-recording checklist

- [ ] 1920×1080, browser zoom 100–110 %, one clean window, bookmarks bar hidden, notifications off
- [ ] Record narration separately or use a decent mic; do a 10-second audio test
- [ ] Sidebar visible but collapsed sections tidy; no API key on screen
- [ ] Show the deployed URL (not `localhost`) at the start
- [ ] Keep the cursor slow; pause 1–2 s on each result so viewers can read it
- [ ] Speed up / trim only the waiting time of AI calls; never alter results
- [ ] Say once that sample images are synthetic if you use them
- [ ] Final length 2:30–3:00; export 1080p MP4; watch it fully once before submitting
- [ ] Tools: OBS Studio, Windows Game Bar (Win+G), macOS Screenshot (Cmd+Shift+5), or Loom
