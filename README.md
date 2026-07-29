# Social Security Optimizer

Compare total value of Social Security benefits (with COLA and optional investment of payments) based on when you file, through a chosen end age.

## Your scenario (defaults)

| Parameter | Value |
|-----------|-------|
| Current age | 64 years, 3 months |
| Monthly benefit if filing now | $3,258 |
| Increase per month delayed (until 70) | +$25/month |
| COLA | 3% / year (default; override on CLI) |
| Investment return on benefits | 4% / year (default; override on CLI) |
| Horizon | Age 85 (default; override on CLI) |

## Model

1. **Filing delay** — For each month you wait (0 through age 70), starting monthly benefit = $3,258 + $25 × wait months.
2. **Collection** — Benefits paid each month from filing until the end age (default 85).
3. **COLA** — Benefit amount increases at the start of each collection year (default 3%; override on CLI).
4. **Investment** — Each month’s payment is added to a portfolio that earns 4% annually by default (compounded monthly).

The portfolio column is the value at the end age if you invest every check at the stated return (not spent on living expenses).

## Run

Install dependencies, then start the web UI (default):

```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000), enter your assumptions, and click **Calculate**.

Optional: `python3 main.py --port 8080` for a different port.

### Terminal table (`--inline`)

```bash
python3 main.py --inline
python3 main.py --inline --investment-return 0.06   # 6% annual return
python3 main.py --inline -r 0.04                   # 4% annual return
python3 main.py --inline --cola 0.035              # 3.5% COLA
python3 main.py --inline -c 0.025 -r 0.05          # 2.5% COLA, 5% return
python3 main.py --inline --end-age 90              # through age 90
python3 main.py --inline -e 80                     # through age 80
```

`python3 webapp.py` still starts the web UI directly.

## Customize

Edit defaults in `calculator.py` (`UserProfile`) or import and call `simulate_scenario` / `all_scenarios` from your own script.

## Requirements

Python 3.9+ and Flask (see `requirements.txt`). The web chart is interactive (hover for values) via Chart.js. Install with `python3 -m pip` if `pip` is not on your PATH.
