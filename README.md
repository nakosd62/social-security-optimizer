# Social Security Optimizer

Find the Social Security filing age (month by month, from now through age 70) that leaves you with the largest portfolio, assuming every after-tax check is invested, and see how that answer depends on how long you live and what your investments earn.

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

## How it works

Enter four numbers and click **Calculate**:

| Field | Meaning | Default |
|-------|---------|---------|
| FRA Benefit ($/mo) | Monthly benefit at Full Retirement Age (from your SSA statement) | $4,000 |
| Tax % | Marginal tax rate applied to benefits | 24% |
| COLA % | Annual cost-of-living increase to your benefit | 3.5% |
| Inflation % | Used to convert all amounts to today's dollars | 3.5% |

The app then finds the best filing age for every combination of:

- **End age** (how long you live): 80 to 90, in 1-year steps
- **Investment return** (actual return, before inflation): 3% to 10%, in 1-point steps

and shows the result as a heatmap (88 squares). Darker squares mean wait longer. Click a square to see that combination's summary (optimal filing age, starting benefit, total benefits, portfolio at the end age, taxes), the range of filing ages within 1% of the best, and a chart of portfolio and total benefits by the age you start.

Every filing age from 62 to 70 is considered. Current age is ignored: it only limits which options are still available, not what each one is worth.

## Model

All amounts are in **today's dollars**: everything is deflated month by month at the inflation rate. The return on the heatmap is the actual investment return, before inflation; its buying power after inflation is roughly return − inflation.

1. **Filing age** — Every month from 62 through 70 is evaluated. Full Retirement Age is fixed at 67 (born 1960 or later).
2. **Benefit adjustment** (SSA rules):
   - Early: −5/9 of 1% per month for the first 36 months before FRA, −5/12 of 1% per month beyond that (62 → 70% of the FRA benefit).
   - Delayed: +2/3 of 1% per month after FRA (70 → 124%).
3. **COLA** — Applied once a year from age 62, including the years before you file (as SSA does). If COLA is below inflation, your benefit loses buying power each year.
4. **Taxes** — 85% of each check is taxed at your marginal rate (the maximum taxable share; actual taxability depends on your other income).
5. **Investment** — Each after-tax check goes into a portfolio earning the stated return, compounded monthly. Investment gains are not taxed.
6. **Optimal** — The filing month with the largest portfolio at the end age.

Reading the heatmap: short lives and high returns favor filing at 62; long lives and low returns favor waiting until 70. Near the boundary the curve is flat, so check the "within 1%" range rather than relying on a single month. Not modeled: spousal/survivor benefits, the earnings test if you work before FRA, and mortality risk.

## Code layout

| File | Purpose |
|------|---------|
| `calculator.py` | Benefit rules and month-by-month simulation (`UserProfile`, `simulate_scenario`, `all_scenarios`) |
| `webapp.py` | Flask app, form handling, heatmap grid |
| `templates/index.html` | Page, heatmap, details and chart (Chart.js) |
| `formatting.py` | Age and money formatting |
| `main.py` | Starts the local server |

## Deploy (Google Cloud Run)

```bash
./gcp_deploy.sh
```

Builds from the `Dockerfile` and deploys service `social-security-optimizer` to `us-east1`, publicly accessible. Requires the `gcloud` CLI, logged in to your project.

## Requirements

Python 3.9+ and Flask (`requirements.txt`).
