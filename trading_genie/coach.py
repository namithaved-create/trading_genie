"""Ask Claude to explain a portfolio health report in plain language."""

from __future__ import annotations

import json

import anthropic

from .portfolio import HealthReport

MODEL = "claude-opus-5-5"

SYSTEM_PROMPT = """\
You are Trading Genie, a warm, patient investing coach for women who are new to \
investing. Your job is education: help the reader understand her own portfolio \
and build confidence, never make her feel behind or judged.

You will receive a JSON health report computed by code. Treat its numbers as \
facts; do not invent prices, returns or holdings that aren't in it.

Write in plain language a smart non-expert understands. When you use a term like \
diversification, concentration risk, sector, expense ratio, index fund or option, explain \
it in one short sentence the first time, using her actual holdings as the example.

Structure your answer in Markdown with these sections:
1. **Your portfolio at a glance**: two or three sentences, including the health score.
2. **What's working**: genuine strengths, if any.
3. **Worth a closer look**: one short paragraph per flag, most important first, \
explaining what it means and why it matters in dollars or percentages from the report.
4. **Questions to explore**: two or three questions she could research or ask a \
financial professional, phrased as learning prompts.

You are an educator, not a financial adviser. Do not tell her to buy or sell any \
specific security, and do not predict prices. It's fine to describe general \
approaches (for example, "many investors use broad index funds to spread risk") \
as context. Keep it under 450 words."""

DISCLAIMER = (
    "Trading Genie is an educational tool, not financial advice. "
    "Consider talking to a licensed financial professional before making investment decisions."
)


class MissingCredentials(Exception):
    """No Anthropic API key (or other credential) is configured."""


def explain(report: HealthReport, client: anthropic.Anthropic | None = None) -> str:
    """Return Claude's Markdown explanation of the report."""
    client = client or anthropic.Anthropic()
    try:
        response = _create(client, report)
    except TypeError as e:
        # The SDK raises TypeError at request time when no credential is set.
        if "authentication method" in str(e):
            raise MissingCredentials from e
        raise
    if response.stop_reason == "refusal":
        return "Sorry, I couldn't generate an explanation for this portfolio. Please try again."
    text = "".join(block.text for block in response.content if block.type == "text")
    if response.stop_reason == "max_tokens":
        text += "\n\n_(The explanation was cut short.)_"
    return text


def _create(client: anthropic.Anthropic, report: HealthReport):
    return client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        output_config={"effort": "medium"},
        # If a safety classifier declines, the API retries on a fallback model.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": "Here is my portfolio health report:\n\n"
                + json.dumps(report.to_dict(), indent=2),
            }
        ],
    )
