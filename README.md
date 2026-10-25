# 🧞‍♀️ Trading Genie

**An AI investing coach that explains your portfolio in plain language, built for women who are starting their investing journey.**

## The problem

Women invest later and less than men and consistently report lower confidence about investing. Career breaks and longer lifespans turn that gap into a real retirement shortfall. Much of the barrier is jargon: words like *diversification*, *concentration risk* and *expense ratio* make it hard to tell whether your own portfolio is in good shape.

## What it does

Trading Genie runs a **portfolio health check**:

1. **Load your holdings** from a CSV, such as a brokerage export, or explore the built-in sample portfolio.
2. **Check the numbers** with transparent, rule-based code:
   - **Concentration risk:** any single stock above 20% of the portfolio
   - **Sector concentration:** any sector above 40%
   - **Fees:** funds charging over 0.50% a year, shown in actual dollars
   - **Cash drag:** more than 20% sitting in cash
   - **Effective diversification:** how many holdings your portfolio *behaves like*
   - A simple **health score** out of 100
3. **Ask the Genie:** Claude turns the report into a friendly explanation. It teaches each concept using your own holdings as the example, says what's working, explains what's worth a closer look, and suggests questions to explore.

### Responsible by design

- **The math is code, not AI.** Claude explains numbers computed deterministically. It doesn't invent them.
- **Education, not advice.** The Genie never tells you to buy or sell a specific security and never predicts prices.
- **Read-only.** Nothing in this project can place a trade.

## Quick start

Requires Python 3.10+ and an [Anthropic API key](https://console.anthropic.com/).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your-key-here
```

**Web app:**

```bash
streamlit run app.py
```

**Command line:**

```bash
python -m trading_genie data/sample_portfolio.csv          # numbers + Claude's explanation
python -m trading_genie data/sample_portfolio.csv --no-ai  # numbers only, no API key needed
```

**Tests:**

```bash
pytest
```

## Portfolio CSV format

| Column | Required | Example | Notes |
|---|---|---|---|
| `symbol` | ✅ | `AAPL` | |
| `shares` | ✅ | `60` | |
| `price` | ✅ | `228.50` | `$` and `,` are fine |
| `name` | | `Apple Inc.` | |
| `type` | | `stock` | `stock`, `fund`/`etf`, or `cash` (default `stock`) |
| `sector` | | `Technology` | Use `Broad Market` or `Diversified` for index funds |
| `expense_ratio` | | `0.03%` | Funds only |

See [`data/sample_portfolio.csv`](data/sample_portfolio.csv).

## How it's built

- `trading_genie/portfolio.py`: CSV parsing and the health-check rules
- `trading_genie/coach.py`: the Claude prompt and API call (Claude Opus 5.5 via the Anthropic Python SDK)
- `app.py`: the Streamlit web app
- `tests/`: unit tests for the rules, parsing and the Claude call (mocked)

## Roadmap

- 📚 **Learning skill:** bite-sized lessons on index funds, diversification and risk, built around your holdings
- 🔌 **Read-only brokerage connection (MCP):** pull holdings automatically instead of uploading a CSV
- 🧪 **Paper-trading sandbox (MCP):** practice trades with pretend money, with every action requiring your approval
- 💬 **Follow-up chat:** ask the Genie questions about your portfolio

---

*Trading Genie is an educational tool, not financial advice. Consider talking to a licensed financial professional before making investment decisions.*
