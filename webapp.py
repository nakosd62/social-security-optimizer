#!/usr/bin/env python3
"""Browser UI for Social Security filing timing analysis."""

from typing import Any, Dict, Optional

from flask import Flask, render_template, request

from calculator import UserProfile, all_scenarios, best_scenario_by_portfolio, months_until_age, simulate_scenario
from formatting import format_age, format_money

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


def build_result_context(profile: UserProfile) -> Dict[str, Any]:
    scenarios = all_scenarios(profile)
    best = best_scenario_by_portfolio(profile)
    end_age = int(profile.analysis_end_age)

    rows = []
    months_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for s in scenarios:
        filing_month_idx = (profile.current_month - 1 + s.wait_months) % 12
        filing_year = profile.current_year + (profile.current_month - 1 + s.wait_months) // 12
        start_date_str = f"{months_names[filing_month_idx]} {filing_year}"
        rows.append(
            {
                "wait_months": s.wait_months,
                "start_date": start_date_str,
                "filing_age": format_age(s.filing_age_years),
                "monthly_benefit": format_money(s.monthly_benefit_at_filing),
                "collection_months": s.collection_months,
                "total_benefits": format_money(s.total_benefits_received),
                "total_taxes": format_money(s.total_taxes_paid),
                "net_benefits": format_money(s.total_net_benefits_received),
                "portfolio": format_money(s.final_portfolio_value),
                "is_best": s.wait_months == best.wait_months,
            }
        )

    best_index = best.wait_months
    portfolio_values = [s.final_portfolio_value for s in scenarios]
    benefit_values = [s.total_benefits_received for s in scenarios]
    labels = [format_age(s.filing_age_years) for s in scenarios]

    # Portfolio growth over time datasets
    total_months = months_until_age(profile.current_age_years, profile.analysis_end_age)
    growth_labels = [
        format_age(profile.current_age_years + m / 12.0)
        for m in range(total_months + 1)
    ]
    
    growth_datasets = []
    
    # 1. Start Now
    now_res = simulate_scenario(profile, 0)
    growth_datasets.append({
        "label": "Start Now",
        "data": now_res.portfolio_history,
        "is_best": now_res.wait_months == best.wait_months
    })
    
    # 2. Target Ages
    added_waits = {0}
    max_w = months_until_age(profile.current_age_years, MAX_FILING_AGE)
    for age in [65.0, 67.0, 70.0]:
        w = months_until_age(profile.current_age_years, age)
        if 0 < w <= max_w and w not in added_waits:
            res = simulate_scenario(profile, w)
            growth_datasets.append({
                "label": f"Start at Age {int(age)}",
                "data": res.portfolio_history,
                "is_best": w == best.wait_months
            })
            added_waits.add(w)

    # 3. Optimal Line
    growth_datasets.append({
        "label": f"Optimal (File at {format_age(best.filing_age_years)})",
        "data": best.portfolio_history,
        "is_best": True
    })

    return {
        "rows": rows,
        "end_age": end_age,
        "chart": {
            "labels": labels,
            "portfolio": portfolio_values,
            "benefits": benefit_values,
            "best_index": best_index,
        },
        "growth_chart": {
            "labels": growth_labels,
            "datasets": growth_datasets,
        },
        "best": {
            "filing_age": format_age(best.filing_age_years),
            "total_benefits": format_money(best.total_benefits_received),
            "total_taxes": format_money(best.total_taxes_paid),
            "net_benefits": format_money(best.total_net_benefits_received),
            "portfolio": format_money(best.final_portfolio_value),
        },
    }


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
