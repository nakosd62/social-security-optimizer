#!/usr/bin/env python3
"""Browser UI for Social Security filing timing analysis.

The user enters an FRA benefit and a tax rate. The app then runs the
filing-age optimization over a grid of end ages x real investment returns
and shows the optimal filing age for each combination as a heatmap.
Clicking a cell shows the details for that combination.

Every filing age from 62 to 70 is considered (current age is ignored; it
only limits which options are still available, not their value). The
benefit grows with COLA each year from 62; all amounts are converted to
today's dollars using the inflation rate. The investment return on the
heatmap axis is the actual (nominal) return, before inflation.
"""

import math
from typing import Any, Dict, List, Optional

from flask import Flask, render_template, request, send_from_directory

from calculator import ScenarioResult, UserProfile, all_scenarios, months_until_age
from formatting import format_age, format_money

app = Flask(__name__)

EARLIEST_FILING_AGE = 62.0
MAX_FILING_AGE = 70.0
END_AGES = list(range(80, 91))          # 80..90, 1-year steps
RETURNS_PCT = list(range(3, 11))        # 3..10 % actual return, 1-point steps
NEAR_OPTIMAL_PCT = 1.0                  # within this % of the best = near-optimal

DEFAULT_FORM = {
    "fra_benefit": "4000",
    "tax_rate_percent": "24",
    "cola_percent": "3.5",
    "inflation_percent": "3.5",
}


def parse_number(form: Dict[str, str], key: str, label: str) -> float:
    try:
        value = float(form[key])
    except (KeyError, ValueError):
        raise ValueError(f"{label} must be a number")
    if not math.isfinite(value):
        raise ValueError(f"{label} must be a number")
    return value


def parse_form(form: Dict[str, str]) -> Dict[str, float]:
    fra_benefit = parse_number(form, "fra_benefit", "FRA benefit")
    tax_pct = parse_number(form, "tax_rate_percent", "Tax rate")
    if not 0 < fra_benefit <= 100_000:
        raise ValueError("FRA benefit must be between $1 and $100,000 per month")
    if not 0 <= tax_pct <= 100:
        raise ValueError("Tax rate must be between 0% and 100%")
    cola_pct = parse_number(form, "cola_percent", "COLA")
    inflation_pct = parse_number(form, "inflation_percent", "Inflation")
    if not 0 <= cola_pct <= 20:
        raise ValueError("COLA must be between 0% and 20%")
    if not -5 <= inflation_pct <= 20:
        raise ValueError("Inflation must be between -5% and 20%")
    return {
        "fra_benefit": fra_benefit,
        "tax_rate": tax_pct / 100.0,
        "cola": cola_pct / 100.0,
        "inflation": inflation_pct / 100.0,
    }


def cell_details(scenarios: List[ScenarioResult], best: ScenarioResult, inflation: float) -> Dict[str, Any]:
    """Summary + chart data for one (end age, return) combination, in today's dollars."""
    threshold = best.real_final_portfolio * (1 - NEAR_OPTIMAL_PCT / 100)
    near = [s for s in scenarios if s.real_final_portfolio >= threshold]
    # Starting check deflated from the month benefits start back to today
    starting_benefit = best.monthly_benefit_at_filing / (1 + inflation) ** (best.wait_months / 12)

    return {
        "best_index": best.wait_months,
        "filing_age": format_age(best.filing_age_years),
        "monthly_benefit": format_money(starting_benefit),
        "total_benefits": format_money(best.real_total_benefits),
        "total_taxes": format_money(best.real_total_taxes),
        "portfolio": format_money(best.real_final_portfolio),
        "near_optimal": {
            "count": len(near),
            "from": format_age(near[0].filing_age_years),
            "to": format_age(near[-1].filing_age_years),
        },
        "portfolio_series": [round(s.real_final_portfolio) for s in scenarios],
        "benefit_series": [round(s.real_total_benefits) for s in scenarios],
    }


def build_grid(fra_benefit: float, tax_rate: float, cola: float, inflation: float) -> Dict[str, Any]:
    rows = []  # one per return, highest return first (top of the heatmap)
    filing_labels: List[str] = []
    for ret in sorted(RETURNS_PCT, reverse=True):
        cells = []
        for end_age in END_AGES:
            profile = UserProfile(
                # The timeline starts at 62 in a January, so COLA is applied
                # every 12 months from 62 (including while waiting to file).
                current_age_years=EARLIEST_FILING_AGE,
                current_month=1,
                fra_benefit=fra_benefit,
                max_filing_age=MAX_FILING_AGE,
                analysis_end_age=float(end_age),
                cola_annual_rate=cola,
                inflation_annual_rate=inflation,
                investment_annual_rate=ret / 100.0,  # actual return; deflated via inflation
                tax_rate=tax_rate,
            )
            scenarios = all_scenarios(profile)
            best = max(scenarios, key=lambda s: s.real_final_portfolio)
            if not filing_labels:
                filing_labels = [format_age(s.filing_age_years) for s in scenarios]
            cells.append(
                {
                    "end_age": end_age,
                    "ret": ret,
                    "best_years": round(best.filing_age_years, 4),
                    "label": format_age(best.filing_age_years),
                    "details": cell_details(scenarios, best, inflation),
                }
            )
        rows.append({"ret": ret, "cells": cells})

    return {
        "end_ages": END_AGES,
        "rows": rows,
        "filing_labels": filing_labels,
        "near_pct": f"{NEAR_OPTIMAL_PCT:g}%",
    }


@app.route("/favicon.ico")
def favicon():
    # Browsers request /favicon.ico directly; serve the PNG icon.
    return send_from_directory(app.static_folder, "favicon-32.png", mimetype="image/png")


@app.route("/", methods=["GET", "POST"])
def index():
    form = dict(DEFAULT_FORM)
    error: Optional[str] = None
    grid: Optional[Dict[str, Any]] = None

    if request.method == "POST":
        form = {key: request.form.get(key, DEFAULT_FORM[key]) for key in DEFAULT_FORM}
        try:
            inputs = parse_form(form)
            grid = build_grid(inputs["fra_benefit"], inputs["tax_rate"], inputs["cola"], inputs["inflation"])
        except ValueError as exc:
            error = str(exc)

    return render_template(
        "index.html",
        form=form,
        error=error,
        grid=grid,
    )


def run_web_server(host: str = "127.0.0.1", port: int = 5000, debug: bool = True) -> None:
    print(f"Open http://{host}:{port} in your browser")
    app.run(debug=debug, host=host, port=port)


if __name__ == "__main__":
    run_web_server()
