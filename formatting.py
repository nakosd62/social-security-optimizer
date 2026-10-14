"""Shared display helpers for CLI and web."""


def format_age(years: float) -> str:
    whole = int(years)
    months = round((years - whole) * 12)
    if months == 12:
        whole += 1
        months = 0
    return f"{whole}y {months}m"


def format_money(amount: float) -> str:
    return f"${amount:,.0f}"


def format_money_delta(amount: float) -> str:
    """Signed money, e.g. +$1,234 / −$1,234."""
    rounded = round(amount)
    if rounded == 0:
        return "$0"
    sign = "+" if rounded > 0 else "\u2212"
    return f"{sign}${abs(rounded):,.0f}"
