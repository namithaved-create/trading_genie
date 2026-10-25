"""Trading Genie web app: streamlit run app.py"""

from __future__ import annotations

from pathlib import Path

import anthropic
import streamlit as st

from trading_genie.coach import DISCLAIMER, MissingCredentials, explain
from trading_genie.portfolio import analyze, parse_holdings

SAMPLE = Path(__file__).parent / "data" / "sample_portfolio.csv"
SEVERITY_ICON = {"high": "🔴", "medium": "🟠", "low": "🟡"}

st.set_page_config(page_title="Trading Genie", page_icon="🧞‍♀️", layout="wide")
st.title("🧞‍♀️ Trading Genie")
st.caption("Your portfolio, explained in plain language. Learn what you own and why it matters.")

uploaded = st.file_uploader(
    "Upload your portfolio CSV (columns: symbol, shares, price; optional: name, type, sector, expense_ratio)",
    type="csv",
)
if uploaded is None:
    st.info("No file yet? Here's a sample beginner portfolio to explore.")
    csv_text = SAMPLE.read_text()
else:
    csv_text = uploaded.getvalue().decode("utf-8-sig")

try:
    report = analyze(parse_holdings(csv_text))
except ValueError as e:
    st.error(f"Couldn't read that portfolio: {e}")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Portfolio value", f"${report.total_value:,.0f}")
c2.metric("Health score", f"{report.score}/100")
c3.metric("Yearly fund fees", f"${report.annual_fees:,.0f}", f"{report.weighted_expense_ratio:.2%} avg", delta_color="off", delta_arrow="off")
c4.metric("Behaves like", f"{report.effective_holdings:.1f} holdings" if report.effective_holdings < 100 else "100+ holdings")

left, right = st.columns([3, 2])
with left:
    st.subheader("What you own")
    st.dataframe(
        report.holdings,
        column_config={
            "symbol": "Symbol",
            "name": "Name",
            "type": "Type",
            "sector": "Sector",
            "weight_pct": st.column_config.ProgressColumn("Weight", format="%.1f%%", min_value=0, max_value=100),
            "value": st.column_config.NumberColumn("Value", format="dollar"),
            "expense_ratio_pct": st.column_config.NumberColumn("Fee %", format="%.2f%%"),
            "annual_fee": st.column_config.NumberColumn("Fee $/yr", format="dollar"),
        },
        hide_index=True,
    )
with right:
    st.subheader("By sector")
    st.bar_chart(report.sector_weights, horizontal=True, y_label="% of portfolio")

st.subheader("Health check")
if report.flags:
    for flag in report.flags:
        st.markdown(f"{SEVERITY_ICON[flag.severity]} **{flag.title}**  \n{flag.detail}")
else:
    st.success("No red flags. Nicely balanced!")

st.subheader("Ask the Genie")
if st.button("✨ Explain my portfolio in plain language", type="primary"):
    with st.spinner("The Genie is reading your portfolio..."):
        try:
            st.markdown(explain(report))
        except MissingCredentials:
            st.error("Claude needs an API key. Set ANTHROPIC_API_KEY before starting the app.")
        except anthropic.AuthenticationError:
            st.error("Claude rejected the API key. Check that ANTHROPIC_API_KEY is correct.")
        except anthropic.APIConnectionError:
            st.error("Couldn't reach Claude. Check your internet connection.")
        except anthropic.APIStatusError as e:
            st.error(f"Claude API error ({e.status_code}): {e.message}")

st.divider()
st.caption(DISCLAIMER)
