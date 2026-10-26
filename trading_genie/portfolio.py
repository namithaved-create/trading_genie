"""Load a portfolio from CSV and compute a plain, rule-based health check.

Everything here is deterministic math: no AI. The numbers it produces are what
Claude is later asked to explain, so the explanations stay grounded in facts.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

REQUIRED_COLUMNS = {"symbol", "shares", "price"}

# Thresholds are deliberately simple rules of thumb, not advice.
SINGLE_STOCK_LIMIT = 0.20  # one company above 20% of the portfolio
SINGLE_STOCK_SEVERE = 0.35
SECTOR_LIMIT = 0.40  # one sector above 40% (ignoring broad funds and cash)
HIGH_EXPENSE_RATIO = 0.0050  # funds charging more than 0.50% a year
CASH_LIMIT = 0.20
OPTIONS_LIMIT = 0.10  # options above 10% of the portfolio
OPTIONS_SEVERE = 0.25
OPTIONS_MAJORITY = 0.50  # above this, the score is capped
OPTIONS_MAJORITY_MAX_SCORE = 40
MIN_EFFECTIVE_HOLDINGS = 5

KINDS = {"stock", "fund", "cash", "option", "crypto"}
KIND_ALIASES = {
    "etf": "fund", "mutual fund": "fund", "index fund": "fund",
    "options": "option", "call": "option", "put": "option",
    "cryptocurrency": "crypto",
}
# Kinds that are a bet on a single company or asset, not a basket.
SINGLE_ASSET_KINDS = {"stock", "option", "crypto"}

# Holdings that are already spread across many companies.
DIVERSIFIED_SECTORS = {"diversified", "broad market", "bonds", "cash"}


@dataclass
class Holding:
    symbol: str
    name: str
    shares: float  # contracts, for options
    price: float  # value of one contract (quoted price x 100), for options
    kind: str  # "stock", "fund", "cash", "option" or "crypto"
    sector: str
    expense_ratio: float  # as a fraction, e.g. 0.0003 for 0.03%

    @property
    def value(self) -> float:
        return self.shares * self.price


@dataclass
class Flag:
    category: str  # "concentration", "sector", "fees", "cash", "diversification"
    severity: str  # "high", "medium" or "low"
    title: str
    detail: str


@dataclass
class HealthReport:
    total_value: float
    holdings: list[dict]
    sector_weights: dict[str, float]
    kind_weights: dict[str, float]
    weighted_expense_ratio: float
    annual_fees: float
    effective_holdings: float
    score: int
    flags: list[Flag] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_value": round(self.total_value, 2),
            "holdings": self.holdings,
            "sector_weights": self.sector_weights,
            "kind_weights": self.kind_weights,
            "weighted_expense_ratio_pct": round(self.weighted_expense_ratio * 100, 3),
            "estimated_annual_fees": round(self.annual_fees, 2),
            "effective_number_of_holdings": round(self.effective_holdings, 1),
            "health_score": self.score,
            "flags": [flag.__dict__ for flag in self.flags],
        }


def _parse_float(raw: str | None, default: float = 0.0) -> float:
    if raw is None or raw.strip() == "":
        return default
    return float(raw.replace("$", "").replace(",", "").replace("%", "").strip())


def _parse_expense_ratio(raw: str | None) -> float:
    """Accept '0.03%', '0.03' (percent) or '0.0003' (fraction)."""
    if raw is None or raw.strip() == "":
        return 0.0
    value = _parse_float(raw)
    # Anything written with % or above 0.05 is a percentage, not a fraction.
    if "%" in raw or value > 0.05:
        return value / 100
    return value


def load_holdings(path: str | Path) -> list[Holding]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return parse_holdings(f.read())


def parse_holdings(text: str) -> list[Holding]:
    reader = csv.DictReader(text.splitlines())
    columns = {c.strip().lower() for c in (reader.fieldnames or [])}
    missing = REQUIRED_COLUMNS - columns
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")

    holdings = []
    for row in reader:
        row = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
        if not row.get("symbol"):
            continue
        kind = (row.get("type") or "stock").lower()
        if kind not in KINDS:
            kind = KIND_ALIASES.get(kind, "stock")
        holdings.append(
            Holding(
                symbol=row["symbol"].upper(),
                name=row.get("name") or row["symbol"].upper(),
                shares=_parse_float(row["shares"]),
                price=_parse_float(row["price"]),
                kind=kind,
                sector=row.get("sector") or ("Cash" if kind == "cash" else "Unknown"),
                expense_ratio=_parse_expense_ratio(row.get("expense_ratio")),
            )
        )
    if not holdings:
        raise ValueError("CSV has no holdings")
    return holdings


def analyze(holdings: list[Holding]) -> HealthReport:
    total = sum(h.value for h in holdings)
    if total <= 0:
        raise ValueError("Portfolio total value must be greater than zero")

    # Weights are per row: a symbol can appear more than once, e.g. a stock
    # and options on it, or two option contracts.
    weights = [h.value / total for h in holdings]

    sector_weights: dict[str, float] = {}
    kind_weights: dict[str, float] = {}
    # Exposure to each single company or asset, adding options to the stock.
    exposure: dict[str, float] = {}
    names: dict[str, str] = {}
    has_options: set[str] = set()
    for h, w in zip(holdings, weights):
        sector_weights[h.sector] = sector_weights.get(h.sector, 0) + w
        kind_weights[h.kind] = kind_weights.get(h.kind, 0) + w
        if h.kind in SINGLE_ASSET_KINDS:
            exposure[h.symbol] = exposure.get(h.symbol, 0) + w
            if h.kind == "option":
                has_options.add(h.symbol)
            else:
                names[h.symbol] = h.name

    weighted_er = sum(w * h.expense_ratio for h, w in zip(holdings, weights))
    annual_fees = sum(h.value * h.expense_ratio for h in holdings)

    # Effective number of holdings (inverse Herfindahl index). A broad index
    # fund counts as many holdings, so only single assets are concentrated bets.
    single_weights = list(exposure.values())
    diversified_weight = 1 - sum(single_weights)
    hhi = sum(w * w for w in single_weights)
    effective = (1 / hhi) if hhi > 0 else float("inf")
    if diversified_weight > 0:
        # Treat the diversified part as spread thinly across a large market.
        effective = 1 / (hhi + (diversified_weight**2) / 500)

    flags = _build_flags(holdings, exposure, names, has_options, sector_weights, kind_weights, effective)
    score = _score(flags)
    # Many small flags can't capture a portfolio that's mostly options.
    if kind_weights.get("option", 0) > OPTIONS_MAJORITY:
        score = min(score, OPTIONS_MAJORITY_MAX_SCORE)

    holding_rows = [
        {
            "symbol": h.symbol,
            "name": h.name,
            "type": h.kind,
            "sector": h.sector,
            "value": round(h.value, 2),
            "weight_pct": round(w * 100, 1),
            "expense_ratio_pct": round(h.expense_ratio * 100, 3),
            "annual_fee": round(h.value * h.expense_ratio, 2),
        }
        for h, w in sorted(zip(holdings, weights), key=lambda hw: hw[0].value, reverse=True)
    ]

    return HealthReport(
        total_value=total,
        holdings=holding_rows,
        sector_weights={k: round(v * 100, 1) for k, v in sorted(sector_weights.items(), key=lambda kv: -kv[1])},
        kind_weights={k: round(v * 100, 1) for k, v in sorted(kind_weights.items(), key=lambda kv: -kv[1])},
        weighted_expense_ratio=weighted_er,
        annual_fees=annual_fees,
        effective_holdings=effective,
        score=score,
        flags=flags,
    )


def _build_flags(holdings, exposure, names, has_options, sector_weights, kind_weights, effective) -> list[Flag]:
    flags: list[Flag] = []

    for symbol, w in exposure.items():
        if w > SINGLE_STOCK_LIMIT:
            name = names.get(symbol, symbol)
            if symbol in has_options:
                # Puts gain when the stock falls, so don't assume a direction.
                detail = (
                    f"Over {SINGLE_STOCK_LIMIT:.0%} of your money depends on how {name}'s stock moves, "
                    "so one big move, up or down, could noticeably change your whole portfolio."
                )
            else:
                detail = (
                    f"A single company above {SINGLE_STOCK_LIMIT:.0%} means one bad year for "
                    f"{name} could noticeably dent your whole portfolio."
                )
            flags.append(
                Flag(
                    "concentration",
                    "high" if w > SINGLE_STOCK_SEVERE else "medium",
                    f"{symbol} is {w:.0%} of your portfolio",
                    detail,
                )
            )

    options = kind_weights.get("option", 0)
    if options > OPTIONS_LIMIT:
        flags.append(
            Flag(
                "options",
                "high" if options > OPTIONS_SEVERE else "medium",
                f"{options:.0%} of your portfolio is in options",
                "An option is a contract that can expire worthless: if the stock doesn't move "
                "far enough before the expiration date, you can lose everything you paid for it. "
                "Options also swing in value much faster than the stocks they're tied to.",
            )
        )

    for sector, w in sector_weights.items():
        if sector.lower() in DIVERSIFIED_SECTORS or sector == "Unknown":
            continue
        if w > SECTOR_LIMIT:
            flags.append(
                Flag(
                    "sector",
                    "medium",
                    f"{w:.0%} of your money is in {sector}",
                    f"Companies in the same sector tend to rise and fall together, so this is "
                    f"less diversified than the number of holdings suggests.",
                )
            )

    for h in holdings:
        if h.kind == "fund" and h.expense_ratio > HIGH_EXPENSE_RATIO:
            fee = h.value * h.expense_ratio
            flags.append(
                Flag(
                    "fees",
                    "medium" if h.expense_ratio > 0.01 else "low",
                    f"{h.symbol} charges {h.expense_ratio:.2%} a year",
                    f"That's about ${fee:,.0f} a year on this holding. Broad index funds often "
                    f"charge under 0.10%.",
                )
            )

    cash = kind_weights.get("cash", 0)
    if cash > CASH_LIMIT:
        flags.append(
            Flag(
                "cash",
                "low",
                f"{cash:.0%} is sitting in cash",
                "Cash is great for an emergency fund, but money you won't need for years "
                "may lose ground to inflation.",
            )
        )

    if effective < MIN_EFFECTIVE_HOLDINGS:
        flags.append(
            Flag(
                "diversification",
                "high" if effective < 3 else "medium",
                f"Your portfolio behaves like about {effective:.1f} holdings",
                "Most of your money rides on a few companies, so their ups and downs drive "
                "your whole portfolio.",
            )
        )

    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(flags, key=lambda f: order[f.severity])


def _score(flags: list[Flag]) -> int:
    penalty = {"high": 20, "medium": 10, "low": 5}
    return max(0, 100 - sum(penalty[f.severity] for f in flags))
