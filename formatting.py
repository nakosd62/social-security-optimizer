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
