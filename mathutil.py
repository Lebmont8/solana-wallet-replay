"""Shared numerical conventions for this standalone replay."""
from decimal import Decimal
import re

D = Decimal
ZERO = D(0)
BPS = D(10_000)


def settings(params, schema):
    if params.keys() - schema.keys():
        raise ValueError("Unknown setting.")
    values = {}
    for key, (label, default, minimum, maximum) in schema.items():
        raw = params.get(key, default)
        if not re.fullmatch(r"[0-9]{1,8}(?:\.[0-9]{1,6})?", raw):
            raise ValueError(f"{label}: enter a decimal number with up to six decimal places.")
        value = D(raw)
        if not D(minimum) <= value <= D(maximum):
            raise ValueError(f"{label}: use a value from {minimum} to {maximum}.")
        values[key] = value
    return values


def fixed(value, places=2):
    return f"{value:,.{places}f}"


def level_fill(levels, requested):
    """Consume up to requested units from ordered (price, available) levels."""
    remaining = requested
    value = ZERO
    fills = []
    for index, (price, available) in enumerate(levels):
        if not remaining:
            break
        size = min(available, remaining)
        if size:
            fills.append((index, size))
            value += size * price
            remaining -= size
    return requested - remaining, value, fills
