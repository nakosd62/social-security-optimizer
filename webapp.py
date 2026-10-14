#!/usr/bin/env python3
"""Browser UI for Social Security filing timing analysis."""

from typing import Any, Dict, Optional

from flask import Flask, render_template, request, send_from_directory

from calculator import ScenarioResult, UserProfile, all_scenarios, months_until_age
from formatting import format_age, format_money, format_money_delta

app = Flask(__name__)

MAX_FILING_AGE = 70.0

DEFAULT_FORM = {
    "current_age_years": "64",
    "current_age_months": "3",
    "fra_benefit": "4000",
    "analysis_end_age": "85",
    "cola_percent": "3",
    "investment_return_percent": "5",
    "tax_rate_percent": "24",
}


def parse_form(form: Dict[str, str]) -> UserProfile:
    years = int(form["current_age_years"])
    months = int(form["current_age_months"])
    if months < 0 or months > 11:
        raise ValueError("Current age months must be between 0 and 11")
    current_age = years + months / 12.0

    if current_age >= MAX_FILING_AGE:
        raise ValueError("Current age must be less than 70 (maximum filing age)")

    profile = UserProfile(
        current_age_years=current_age,
        fra_age_years=67.0,
        fra_benefit=float(form["fra_benefit"]),
        max_filing_age=MAX_FILING_AGE,
        analysis_end_age=float(form["analysis_end_age"]),
        cola_annual_rate=float(form["cola_percent"]) / 100.0,
        investment_annual_rate=float(form["investment_return_percent"]) / 100.0,
        tax_rate=float(form["tax_rate_percent"]) / 100.0,
    )
    if profile.analysis_end_age <= profile.current_age_years:
        raise ValueError("End age must be greater than your current age")
    if profile.fra_benefit < 0:
        raise ValueError("FRA benefit must be non-negative")
    if profile.cola_annual_rate < 0 or profile.investment_annual_rate < 0:
        raise ValueError("COLA and investment return must be non-negative")
    if profile.tax_rate < 0 or profile.tax_rate > 1:
        raise ValueError("Tax rate must be between 0% and 100%")
    return profile


NEAR_OPTIMAL_PCT = 1.0  # filing ages within this % of the best are "near-optimal"


def money_pair(nominal: float, real: float) -> Dict[str, str]:
    """Same amount in nominal and today's dollars, for the toggle in the UI."""
    return {"n": format_money(nominal), "r": format_money(real)}


def delta_pair(nominal: float, real: float) -> Dict[str, str]:
    return {"n": format_money_delta(nominal), "r": format_money_delta(real)}


def build_result_context(profile: UserProfile) -> Dict[str, Any]:
    scenarios = all_scenarios(profile)
    best = max(scenarios, key=lambda s: s.final_portfolio_value)
    end_age = int(profile.analysis_end_age)
    max_w = len(scenarios) - 1

    def filing_label(s: ScenarioResult) -> str:
        return format_age(s.filing_age_years)

    rows = []
    months_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for s in scenarios:
        filing_month_idx = (profile.current_month - 1 + s.wait_months) % 12
        filing_year = profile.current_year + (profile.current_month - 1 + s.wait_months) // 12
        is_best = s.wait_months == best.wait_months
        rows.append(
            {
                "wait_months": s.wait_months,
                "start_date": f"{months_names[filing_month_idx]} {filing_year}",
                "filing_age": filing_label(s),
                "monthly_benefit": format_money(s.monthly_benefit_at_filing),
                "collection_months": s.collection_months,
                "total_benefits": money_pair(s.total_benefits_received, s.real_total_benefits),
                "total_taxes": money_pair(s.total_taxes_paid, s.real_total_taxes),
                "net_benefits": money_pair(s.total_net_benefits_received, s.real_net_benefits),
                "portfolio": money_pair(s.final_portfolio_value, s.real_final_portfolio),
                "vs_best": None if is_best else delta_pair(
                    s.final_portfolio_value - best.final_portfolio_value,
                    s.real_final_portfolio - best.real_final_portfolio,
                ),
                "is_best": is_best,
            }
        )

    # How much the optimum beats common alternatives
    comparisons = []
    alternatives = [("now", 0)]
    for age in (67.0, 70.0):
        w = months_until_age(profile.current_age_years, age)
        if 0 < w <= max_w:
            alternatives.append((f"at {int(age)}", w))
    for label, w in alternatives:
        alt = scenarios[w]
        if w == best.wait_months:
            continue
        gain = best.final_portfolio_value - alt.final_portfolio_value
        pct = gain / alt.final_portfolio_value * 100 if alt.final_portfolio_value > 0 else None
        comparisons.append(
            {
                "label": f"{label} ({filing_label(alt)})",
                "gain": delta_pair(gain, best.real_final_portfolio - alt.real_final_portfolio),
                "pct": f"{pct:.1f}%" if pct is not None else "n/a",
            }
        )

    # Range of filing ages that end up within NEAR_OPTIMAL_PCT of the best
    threshold = best.final_portfolio_value * (1 - NEAR_OPTIMAL_PCT / 100)
    near = [s for s in scenarios if s.final_portfolio_value >= threshold]
    near_optimal = {
        "pct": f"{NEAR_OPTIMAL_PCT:g}%",
        "from": filing_label(near[0]),
        "to": filing_label(near[-1]),
        "count": len(near),
        "amount": money_pair(
            best.final_portfolio_value * NEAR_OPTIMAL_PCT / 100,
            best.real_final_portfolio * NEAR_OPTIMAL_PCT / 100,
        ),
    }

    # Portfolio growth over time: start now, ages 65/67/70, and the optimum
    total_months = months_until_age(profile.current_age_years, profile.analysis_end_age)
    growth_labels = [format_age(profile.current_age_years + m / 12.0) for m in range(total_months + 1)]

    def growth_dataset(label: str, s: ScenarioResult) -> Dict[str, Any]:
        return {
            "label": label,
            "data": {"n": s.portfolio_history, "r": s.real_portfolio_history},
            "is_best": s.wait_months == best.wait_months,
        }

    growth_datasets = [growth_dataset("Start Now", scenarios[0])]
    added_waits = {0}
    for age in (65.0, 67.0, 70.0):
        w = months_until_age(profile.current_age_years, age)
        if 0 < w <= max_w and w not in added_waits:
            growth_datasets.append(growth_dataset(f"Start at Age {int(age)}", scenarios[w]))
            added_waits.add(w)
    growth_datasets.append(growth_dataset(f"Optimal (File at {filing_label(best)})", best))

    return {
        "rows": rows,
        "end_age": end_age,
        "inflation_pct": f"{profile.cola_annual_rate * 100:g}%",
        "comparisons": comparisons,
        "near_optimal": near_optimal,
        "chart": {
            "labels": [filing_label(s) for s in scenarios],
            "portfolio": {
                "n": [s.final_portfolio_value for s in scenarios],
                "r": [s.real_final_portfolio for s in scenarios],
            },
            "benefits": {
                "n": [s.total_benefits_received for s in scenarios],
                "r": [s.real_total_benefits for s in scenarios],
            },
            "best_index": best.wait_months,
        },
        "growth_chart": {
            "labels": growth_labels,
            "datasets": growth_datasets,
        },
        "best": {
            "filing_age": filing_label(best),
            "total_benefits": money_pair(best.total_benefits_received, best.real_total_benefits),
            "total_taxes": money_pair(best.total_taxes_paid, best.real_total_taxes),
            "net_benefits": money_pair(best.total_net_benefits_received, best.real_net_benefits),
            "portfolio": money_pair(best.final_portfolio_value, best.real_final_portfolio),
        },
    }


@app.route("/favicon.ico")
def favicon():
    # Browsers request /favicon.ico directly; serve the PNG icon.
    return send_from_directory(app.static_folder, "favicon-32.png", mimetype="image/png")


@app.route("/", methods=["GET", "POST"])
def index():
    form = dict(DEFAULT_FORM)
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

    if request.method == "POST":
        form = {key: request.form.get(key, DEFAULT_FORM.get(key, "")) for key in DEFAULT_FORM}
        try:
            profile = parse_form(form)
            result = build_result_context(profile)
        except (ValueError, TypeError) as exc:
            error = str(exc)

    return render_template("index.html", form=form, error=error, result=result)


def run_web_server(host: str = "127.0.0.1", port: int = 5000, debug: bool = True) -> None:
    print(f"Open http://{host}:{port} in your browser")
    app.run(debug=debug, host=host, port=port)


if __name__ == "__main__":
    run_web_server()
