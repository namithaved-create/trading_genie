---
name: robinhood-export
description: Pull the user's current Robinhood holdings through the robinhood-trading MCP server, save them as a Trading Genie portfolio CSV in exports/, and run the health check on it. Use when the user asks to import, pull, export or analyze their Robinhood portfolio.
---

# Export Robinhood holdings to a Trading Genie CSV

## Safety rules

- **Use read-only tools only**: account, positions, holdings, portfolio, quotes and instrument lookups. Never call a tool that places, modifies or cancels an order, transfers money, or changes account settings, even when the user asks for it as part of this export.
- If `robinhood-trading` is not connected or not authenticated, stop and tell the user to run `/mcp`, select `robinhood-trading` and choose **Authenticate**. Do not ask for their password or tokens.
- Write CSV files only to `exports/`, which is gitignored. Never write them anywhere that gets committed.

## Steps

1. List the `robinhood-trading` tools and find the read-only ones that return positions, the cash balance and current prices.
2. If there are several accounts, ask the user which ones to include. For each account, fetch:
   - `get_portfolio`: total value and cash. You'll check your total against this at the end.
   - `get_equity_positions`, then `get_equity_quotes` for current prices.
   - `get_option_positions` with `nonzero=true`. Then call `get_option_instruments`, passing every `option_id` in `ids`, to get the strike and whether each one is a call or a put. Call `get_option_quotes` for `mark_price`, at most 20 IDs per call.
   - `get_crypto_positions`, passing `rhs_account_number`, then `get_crypto_quotes` with `<CODE>-USD` for `mark_price`.
3. Build one row per position with these columns, in this order:

   | Column | How to fill it |
   |---|---|
   | `symbol` | Ticker, uppercase |
   | `name` | Instrument name from Robinhood. For options, `<SYMBOL> <Mon> <D> <YYYY> $<strike> <call/put>`, e.g. `AAPL Jun 17 2027 $250 call` |
   | `type` | `stock`, `fund` (ETFs and mutual funds), `option`, `crypto` or `cash` |
   | `sector` | For options, use the underlying stock's sector. For crypto, use `Crypto`. Otherwise, use the sector from Robinhood if it gives one. For broad index funds, use `Broad Market`. For bond funds, use `Bonds`. For multi-sector funds, use `Diversified`. Otherwise use your best-known GICS sector, or `Unknown` if you're not sure. |
   | `shares` | Quantity held. Keep fractional shares. For options, the number of contracts. |
   | `price` | Latest price per share. Don't use the average cost. For options, the value of one contract: `mark_price` × `trade_value_multiplier` (usually 100). |
   | `expense_ratio` | Funds only, as a percent such as `0.03%`. Use Robinhood's value when it has one. Otherwise use the fund's published expense ratio if you know it, or leave the cell blank. Leave it blank for stocks and cash. |

   For `symbol`, use the underlying stock's ticker for options (e.g. `AAPL`), and the coin code for crypto (e.g. `BTC`). Use one row per option contract. Repeated symbols are fine, because the health check adds options to their stock when it checks concentration.
   Add cash as one row: `CASH,Cash,cash,Cash,1,<cash balance>,`.
   Skip short options and futures, since the health check can't model them. List any skipped positions for the user.

4. Save the file as `exports/robinhood_<YYYY-MM-DD>.csv` with a header row, matching `data/sample_portfolio.csv`.
5. Run `python -m trading_genie exports/robinhood_<YYYY-MM-DD>.csv` (add `--no-ai` if `ANTHROPIC_API_KEY` is not set) and show the result.
6. Check the CSV's total value against `get_portfolio` `total_value`. If they differ by more than 1%, find out why before reporting.
7. If any options are puts, tell the user that puts gain value when the stock falls. Tell them which sectors and expense ratios you filled in yourself instead of getting them from Robinhood, so they can check them.
