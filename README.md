# Social Security Optimizer

Find the Social Security filing age (month by month, from now through age 70) that leaves you with the largest portfolio at a chosen end age, assuming every after-tax check is invested.

## Run locally

First time only — create a virtual environment and install dependencies:

```bash
cd ~/Coding/social-security-optimizer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Every time after that:

```bash
cd ~/Coding/social-security-optimizer
source .venv/bin/activate
python3 main.py
```

Then open <http://127.0.0.1:5000>, enter your numbers, and click **Calculate**. Stop the server with `Ctrl+C`.

Options: `python3 main.py --port 8080` (different port), `--host 0.0.0.0` (reachable from other devices on your network).

## Inputs (web form)

| Field | Meaning | Form default |
|-------|---------|--------------|
| Age (y / mo) | Your current age | 64 y 3 m |
| FRA Benefit ($/mo) | Monthly benefit at Full Retirement Age (from your SSA statement) | $4,000 |
| End age | Age the analysis runs to | 85 |
| COLA % | Annual cost-of-living adjustment | 3% |
| Return % | Annual return on invested benefits | 5% |
| Tax % | Marginal tax rate applied to benefits | 24% |

## Model

1. **Filing age** — Every month from now through age 70 is evaluated. Full Retirement Age is fixed at 67 (born 1960 or later).
2. **Benefit adjustment** (SSA rules):
   - Early: −5/9 of 1% per month for the first 36 months before FRA, −5/12 of 1% per month beyond that (62 → 70% of the FRA benefit).
   - Delayed: +2/3 of 1% per month after FRA (70 → 124%).
3. **COLA** — Applied every January, including the years before you file.
4. **Taxes** — 85% of each check is taxed at your marginal rate (the maximum taxable share; actual taxability depends on your other income).
5. **Investment** — Each after-tax check goes into a portfolio earning the stated return, compounded monthly. Investment gains are not taxed.
6. **Optimal** — The filing month with the largest portfolio at the end age.

The result depends heavily on the end age: earlier end ages favor filing now, later ones favor waiting until 70. Try a few. Not modeled: spousal/survivor benefits, the earnings test if you work before FRA, and mortality risk.

## Code layout

| File | Purpose |
|------|---------|
| `calculator.py` | Benefit rules and month-by-month simulation (`UserProfile`, `simulate_scenario`, `all_scenarios`) |
| `webapp.py` | Flask app and form handling |
| `templates/index.html` | Page, charts (Chart.js), results table |
| `formatting.py` | Age and money formatting |
| `main.py` | Starts the local server |

## Deploy (Google Cloud Run)

```bash
./gcp_deploy.sh
```

Builds from the `Dockerfile` and deploys service `social-security-optimizer` to `us-east1`, publicly accessible. Requires the `gcloud` CLI, logged in to your project.

## Requirements

Python 3.9+ and Flask (`requirements.txt`).
