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
   - **Options:** more than 10% in options, which can expire worthless. When options are over half the portfolio, the health score is capped at 40.
   - **Effective diversification:** how many holdings your portfolio *behaves like*
   - A simple **health score** out of 100
3. **Ask the Genie:** Claude turns the report into a friendly explanation. It teaches each concept using your own holdings as the example, says what's working, explains what's worth a closer look, and suggests questions to explore.

### Responsible by design

- **The math is code, not AI.** Claude explains numbers computed deterministically. It doesn't invent them.
- **Education, not advice.** The Genie never tells you to buy or sell a specific security and never predicts prices.
- **Read-only.** The app's code can't place trades. The optional Claude Code Robinhood connection below can, but only after you approve each action.

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

## Connect your Robinhood account (Claude Code)

This repo includes a [`.mcp.json`](.mcp.json) that registers Robinhood's MCP server with [Claude Code](https://claude.com/claude-code). Each person signs in with their own Robinhood account, and no credentials are stored in the repo.

1. Open this project in Claude Code. When asked, approve the `robinhood-trading` server from `.mcp.json`.
2. Run `/mcp`, select `robinhood-trading`, and choose **Authenticate**. Log in to Robinhood in the browser window that opens.
3. Run `/robinhood-export`, or just say *"Pull my Robinhood holdings and run a health check."* Claude reads your positions and saves them in the CSV format below as `exports/robinhood_<date>.csv`. That folder is gitignored. Claude then runs the health check on the file.

> ⚠️ This server can place real trades. Claude Code asks before each tool call, so read the request before approving, and don't approve any call that would place an order unless you mean it.

## Portfolio CSV format

| Column | Required | Example | Notes |
|---|---|---|---|
| `symbol` | ✅ | `AAPL` | |
| `shares` | ✅ | `60` | |
| `price` | ✅ | `228.50` | `$` and `,` are fine |
| `name` | | `Apple Inc.` | |
| `type` | | `stock` | `stock`, `fund`/`etf`, `option`, `crypto` or `cash` (default `stock`) |
| `sector` | | `Technology` | Use `Broad Market` or `Diversified` for index funds |
| `expense_ratio` | | `0.03%` | Funds only |

For an **option**, use the underlying stock's ticker as `symbol` and the number of contracts as `shares`. Set `price` to the current value of one contract, which is the quoted price × 100. Options count toward their stock in the concentration check, and the health check flags any portfolio with more than 10% in options.

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
