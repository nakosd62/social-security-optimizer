import datetime
from dataclasses import dataclass, field


@dataclass(frozen=True)
class UserProfile:
    """Inputs for benefit timing analysis."""

    current_age_years: float = 64.25  # 64 years 3 months
    fra_age_years: float = 67.0       # Full Retirement Age
    fra_benefit: float = 3000.0       # Monthly benefit if filing at FRA
    # Evaluated each time a profile is created (not once at import), so a
    # long-running server always uses today's month/year.
    current_month: int = field(default_factory=lambda: datetime.date.today().month)
    current_year: int = field(default_factory=lambda: datetime.date.today().year)
    max_filing_age: float = 70.0
    analysis_end_age: float = 85.0
    cola_annual_rate: float = 0.03
    investment_annual_rate: float = 0.04
    tax_rate: float = 0.24


@dataclass(frozen=True)
class ScenarioResult:
    """Outcome for one filing delay choice."""

    wait_months: int
    filing_age_years: float
    monthly_benefit_at_filing: float
    collection_months: int
    total_benefits_received: float
    total_taxes_paid: float
    total_net_benefits_received: float
    final_portfolio_value: float
    total_nominal_value: float  # benefits + investment growth (final portfolio)
    portfolio_history: list[float]
    # Same figures in today's dollars (deflated month by month at the COLA rate)
    real_total_benefits: float = 0.0
    real_total_taxes: float = 0.0
    real_net_benefits: float = 0.0
    real_final_portfolio: float = 0.0
    real_portfolio_history: list[float] = field(default_factory=list)


def months_until_age(from_age_years: float, target_age_years: float) -> int:
    return max(0, round((target_age_years - from_age_years) * 12))


def monthly_rate(annual_rate: float) -> float:
    return (1.0 + annual_rate) ** (1.0 / 12.0) - 1.0


def benefit_factor(months_from_fra: int) -> float:
    """
    Fraction of the FRA benefit paid when filing `months_from_fra` months
    relative to Full Retirement Age (negative = early, positive = delayed).

    Early: -5/9 of 1% per month for the first 36 months, then -5/12 of 1%
    per additional month (SSA rules). Delayed: +2/3 of 1% per month (8%/yr).
    """
    if months_from_fra < 0:
        early = -months_from_fra
        first = min(early, 36)
        extra = early - first
        return 1.0 - first * (5 / 9) / 100 - extra * (5 / 12) / 100
    return 1.0 + months_from_fra * (2 / 3) / 100


def monthly_benefit_at_filing(profile: UserProfile, wait_months: int) -> float:
    max_wait = months_until_age(profile.current_age_years, profile.max_filing_age)
    wait = min(wait_months, max_wait)

    current_age_months = round(profile.current_age_years * 12)
    fra_months = round(profile.fra_age_years * 12)
    filing_age_months = current_age_months + wait
    months_diff = filing_age_months - fra_months

    benefit = profile.fra_benefit * benefit_factor(months_diff)

    # Apply COLA during wait months when calendar month is January
    for m in range(1, wait + 1):
        cal_month = (profile.current_month - 1 + m) % 12 + 1
        if cal_month == 1:
            benefit *= (1.0 + profile.cola_annual_rate)

    return benefit


def simulate_scenario(profile: UserProfile, wait_months: int) -> ScenarioResult:
    """
    Simulate from current age until analysis_end_age.

    Each month: portfolio earns investment return, then monthly benefit is deposited if collecting.
    COLA is applied to the monthly benefit every January.
    """
    max_wait = months_until_age(profile.current_age_years, profile.max_filing_age)
    wait = min(wait_months, max_wait)

    filing_age = profile.current_age_years + wait / 12.0
    collection_months = months_until_age(filing_age, profile.analysis_end_age)
    total_months = months_until_age(profile.current_age_years, profile.analysis_end_age)

    if collection_months <= 0:
        return ScenarioResult(
            wait_months=wait,
            filing_age_years=filing_age,
            monthly_benefit_at_filing=monthly_benefit_at_filing(profile, wait),
            collection_months=0,
            total_benefits_received=0.0,
            total_taxes_paid=0.0,
            total_net_benefits_received=0.0,
            final_portfolio_value=0.0,
            total_nominal_value=0.0,
            portfolio_history=[0.0] * (total_months + 1),
            real_portfolio_history=[0.0] * (total_months + 1),
        )

    current_age_months = round(profile.current_age_years * 12)
    fra_months = round(profile.fra_age_years * 12)
    filing_age_months = current_age_months + wait
    months_diff = filing_age_months - fra_months

    running_benefit = profile.fra_benefit * benefit_factor(months_diff)
    invest_r = monthly_rate(profile.investment_annual_rate)
    # Inflation is assumed equal to COLA (COLA is CPI-indexed).
    inflation_r = monthly_rate(profile.cola_annual_rate)

    portfolio = 0.0
    benefits_sum = 0.0
    taxes_sum = 0.0
    net_benefits_sum = 0.0
    portfolio_history = [0.0]
    real_benefits_sum = 0.0
    real_taxes_sum = 0.0
    real_net_sum = 0.0
    real_portfolio_history = [0.0]

    for m in range(1, total_months + 1):
        cal_month = (profile.current_month - 1 + m) % 12 + 1
        if cal_month == 1:
            running_benefit *= (1.0 + profile.cola_annual_rate)

        if m > wait:
            tax = running_benefit * 0.85 * profile.tax_rate
            net_benefit = running_benefit - tax
            portfolio = portfolio * (1.0 + invest_r) + net_benefit
            benefits_sum += running_benefit
            taxes_sum += tax
            net_benefits_sum += net_benefit
            deflator = (1.0 + inflation_r) ** m
            real_benefits_sum += running_benefit / deflator
            real_taxes_sum += tax / deflator
            real_net_sum += net_benefit / deflator
        else:
            portfolio = portfolio * (1.0 + invest_r)

        portfolio_history.append(portfolio)
        real_portfolio_history.append(portfolio / (1.0 + inflation_r) ** m)

    return ScenarioResult(
        wait_months=wait,
        filing_age_years=filing_age,
        monthly_benefit_at_filing=monthly_benefit_at_filing(profile, wait),
        collection_months=collection_months,
        total_benefits_received=benefits_sum,
        total_taxes_paid=taxes_sum,
        total_net_benefits_received=net_benefits_sum,
        final_portfolio_value=portfolio,
        total_nominal_value=portfolio,
        portfolio_history=portfolio_history,
        real_total_benefits=real_benefits_sum,
        real_total_taxes=real_taxes_sum,
        real_net_benefits=real_net_sum,
        real_final_portfolio=real_portfolio_history[-1],
        real_portfolio_history=real_portfolio_history,
    )


def all_scenarios(profile: UserProfile) -> list[ScenarioResult]:
    max_wait = months_until_age(profile.current_age_years, profile.max_filing_age)
    return [simulate_scenario(profile, w) for w in range(max_wait + 1)]


def best_scenario_by_portfolio(profile: UserProfile) -> ScenarioResult:
    scenarios = all_scenarios(profile)
    return max(scenarios, key=lambda s: s.final_portfolio_value)
