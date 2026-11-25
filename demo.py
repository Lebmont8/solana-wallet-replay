"""Replay owner-level SPL token balance changes without a signer or RPC."""
from collections import defaultdict

from mathutil import BPS, D, ZERO, fixed, settings

SCHEMA = {
    "budget": ("Starting balance", "75", "1", "100000"),
    "clip": ("Size per buy", "20", "0.01", "100000"),
    "cap": ("Maximum source price", "3", "0.01", "100000"),
    "fee": ("Simulated fee", "30", "0", "1000"),
}


def owned_balances(entries, owner):
    totals = defaultdict(lambda: ZERO)
    for entry in entries:
        if entry.get("owner") == owner:
            raw = entry["uiTokenAmount"]
            totals[entry["mint"]] += D(raw["amount"]).scaleb(-raw["decimals"])
    return totals


def decode_swap(event, owner, quote):
    meta = event["meta"]
    if meta["err"] is not None:
        return None, "Source transaction failed"
    before = owned_balances(meta["preTokenBalances"], owner)
    after = owned_balances(meta["postTokenBalances"], owner)
    changes = {mint: after[mint] - before[mint] for mint in before.keys() | after.keys()}
    base = [(mint, change) for mint, change in changes.items() if mint != quote and change]
    cash = changes.get(quote, ZERO)
    if not cash or len(base) != 1 or base[0][1] * cash >= 0:
        return None, "Not an unambiguous quote-token swap"
    mint, quantity = base[0]
    return (mint, quantity, abs(cash / quantity)), ""


def run(fixture, params):
    config = settings(params, SCHEMA)
    fee_rate = config["fee"] / BPS
    balance = config["budget"]
    holdings = defaultdict(lambda: ZERO)
    seen = set()
    rows = []
    copied = 0
    fees = ZERO
    names = fixture["symbols"]
    for event in sorted(fixture["transactions"], key=lambda entry: (entry["slot"], entry["order"])):
        signature = event["transaction"]["signatures"][0]
        if signature in seen:
            continue
        seen.add(signature)
        slot = str(event["slot"])
        swap, reason = decode_swap(event, fixture["owner"], fixture["quote"])
        if swap is None:
            rows.append([slot, "—", "—", "Skipped", "—", reason])
            continue
        mint, amount, price = swap
        symbol = names.get(mint, mint)
        side = "Buy" if amount > 0 else "Sell"
        status = "Skipped"
        quantity = ZERO
        if side == "Buy":
            gross = config["clip"]
            fee = gross * fee_rate
            if price > config["cap"]:
                reason = "Source price exceeds buy cap"
            elif gross + fee > balance:
                reason = "Insufficient simulated USDC"
            else:
                quantity = gross / price
                holdings[mint] += quantity
                balance -= gross + fee
                reason = "Fixed-size copy"
        elif holdings[mint]:
            quantity = min(abs(amount), holdings[mint])
            gross = quantity * price
            fee = gross * fee_rate
            holdings[mint] -= quantity
            balance += gross - fee
            reason = "Capped at source sell size and available inventory"
        else:
            reason = "No copied inventory to sell"
        if quantity:
            status = "Copied"
            copied += 1
            fees += fee
        rows.append([
            slot, f"{side} {symbol}", fixed(price, 4), status,
            fixed(quantity, 4) if quantity else "—", reason,
        ])
    return {
        "metrics": [
            ["Copied swaps", str(copied)],
            ["Skipped transactions", str(len(rows) - copied)],
            ["Cash remaining (USDC)", fixed(balance)],
            ["Simulated fees (USDC)", fixed(fees)],
        ],
        "columns": ["Slot", "Source", "USDC / token", "Decision", "Copied units", "Reason"],
        "rows": rows,
        "note": "Synthetic SPL balances. Trades are simulated; holdings are not marked to market.",
    }
