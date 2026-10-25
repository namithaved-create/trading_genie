from pathlib import Path
from types import SimpleNamespace

import pytest

from trading_genie import coach
from trading_genie.portfolio import analyze, load_holdings, parse_holdings

SAMPLE = Path(__file__).parent.parent / "data" / "sample_portfolio.csv"


def categories(report):
    return [f.category for f in report.flags]


def test_sample_portfolio_flags_apple_and_tech():
    report = analyze(load_holdings(SAMPLE))
    assert report.total_value == pytest.approx(36065.20)
    assert report.holdings[0]["symbol"] == "AAPL"
    assert report.flags[0].category == "concentration"
    assert report.flags[0].severity == "high"
    assert "sector" in categories(report)
    assert categories(report).count("fees") == 2
    assert report.annual_fees == pytest.approx(3620 * 0.0059 + 1950 * 0.0075 + 4200 * 0.0003)
    assert report.score == 60


def test_index_fund_portfolio_is_healthy():
    report = analyze(parse_holdings(
        "symbol,type,sector,shares,price,expense_ratio\n"
        "VTI,fund,Broad Market,100,280,0.03%\n"
        "VXUS,fund,Diversified,100,62,0.08%\n"
        "BND,fund,Bonds,50,72,0.03%\n"
    ))
    assert report.flags == []
    assert report.score == 100


def test_large_index_fund_is_not_concentration_risk():
    report = analyze(parse_holdings("symbol,type,sector,shares,price\nVOO,fund,Broad Market,10,500\n"))
    assert "concentration" not in categories(report)


def test_few_stocks_flags_diversification():
    report = analyze(parse_holdings(
        "symbol,sector,shares,price\nAAPL,Technology,10,100\nJPM,Financials,10,100\n"
    ))
    assert "diversification" in categories(report)


def test_too_much_cash_is_flagged():
    report = analyze(parse_holdings(
        "symbol,type,shares,price\nCASH,cash,1,5000\nVTI,fund,10,280\n"
    ))
    assert "cash" in categories(report)


@pytest.mark.parametrize("raw, expected", [("0.75%", 0.0075), ("0.75", 0.0075), ("0.0075", 0.0075), ("", 0.0)])
def test_expense_ratio_formats(raw, expected):
    report = analyze(parse_holdings(
        f"symbol,type,shares,price,expense_ratio\nXYZ,fund,1,100,{raw}\n"
    ))
    assert report.weighted_expense_ratio == pytest.approx(expected)


def test_handles_dollar_signs_and_commas():
    holdings = parse_holdings('symbol,shares,price\nAAPL,"1,000",$228.50\n')
    assert holdings[0].value == pytest.approx(228500)


def test_missing_columns_raises():
    with pytest.raises(ValueError, match="price"):
        parse_holdings("symbol,shares\nAAPL,10\n")


def test_explain_sends_report_and_returns_text():
    calls = {}

    class FakeMessages:
        def create(self, **kwargs):
            calls.update(kwargs)
            return SimpleNamespace(
                stop_reason="end_turn",
                content=[SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text="Hello!")],
            )

    fake_client = SimpleNamespace(beta=SimpleNamespace(messages=FakeMessages()))
    report = analyze(load_holdings(SAMPLE))

    assert coach.explain(report, client=fake_client) == "Hello!"
    assert calls["model"] == "claude-opus-5-5"
    assert "AAPL" in calls["messages"][0]["content"]
