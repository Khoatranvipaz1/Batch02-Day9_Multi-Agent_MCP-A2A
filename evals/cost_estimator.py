"""Offline LLM call and cost estimator for the Day 9 agent network.

This module never contacts OpenRouter. Prices are planning inputs and can be
overridden from the command line or environment when provider pricing changes.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_MODEL = "google/gemini-2.5-flash-lite"
DEFAULT_INPUT_PRICE_PER_M = 0.10
DEFAULT_OUTPUT_PRICE_PER_M = 0.40


@dataclass(frozen=True)
class CallEstimate:
    agent: str
    purpose: str
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class CostEstimate:
    model: str
    scenario: str
    queries: int
    llm_calls_per_query: int
    input_tokens_per_query: int
    output_tokens_per_query: int
    input_price_per_m: float
    output_price_per_m: float
    estimated_cost_per_query_usd: float
    estimated_total_cost_usd: float
    calls: list[CallEstimate]


def classify_scenario(question: str) -> str:
    """Classify a question without using an LLM."""
    lowered = question.lower()
    needs_tax = any(
        keyword in lowered
        for keyword in ["tax", "irs", "thuế", "fbar", "fatca"]
    )
    needs_compliance = any(
        keyword in lowered
        for keyword in [
            "compliance",
            "sec",
            "sox",
            "aml",
            "fcpa",
            "regulation",
            "tuân thủ",
        ]
    )
    if needs_tax and needs_compliance:
        return "both"
    if needs_tax:
        return "tax"
    if needs_compliance:
        return "compliance"
    return "legal"


def build_call_plan(scenario: str, question_tokens: int = 40) -> list[CallEstimate]:
    """Return the expected production call graph for one user question."""
    if scenario not in {"legal", "tax", "compliance", "both"}:
        raise ValueError(f"Unsupported scenario: {scenario}")

    calls = [
        CallEstimate(
            agent="law",
            purpose="general legal analysis",
            input_tokens=150 + question_tokens,
            output_tokens=350,
        ),
    ]

    specialist_output_tokens = 0
    if scenario in {"tax", "both"}:
        calls.append(
            CallEstimate(
                agent="tax",
                purpose="specialist tax analysis",
                input_tokens=420 + question_tokens,
                output_tokens=350,
            )
        )
        specialist_output_tokens += 350

    if scenario in {"compliance", "both"}:
        calls.append(
            CallEstimate(
                agent="compliance",
                purpose="specialist compliance analysis",
                input_tokens=470 + question_tokens,
                output_tokens=350,
            )
        )
        specialist_output_tokens += 350

    calls.append(
        CallEstimate(
            agent="law",
            purpose="aggregate legal and specialist analyses",
            input_tokens=650 + 350 + specialist_output_tokens,
            output_tokens=450,
        )
    )
    return calls


def estimate_cost(
    scenario: str,
    queries: int = 1,
    question_tokens: int = 40,
    model: str = DEFAULT_MODEL,
    input_price_per_m: float = DEFAULT_INPUT_PRICE_PER_M,
    output_price_per_m: float = DEFAULT_OUTPUT_PRICE_PER_M,
) -> CostEstimate:
    """Estimate tokens and cost without sending an API request."""
    if queries < 1:
        raise ValueError("queries must be at least 1")

    calls = build_call_plan(scenario, question_tokens)
    input_tokens = sum(call.input_tokens for call in calls)
    output_tokens = sum(call.output_tokens for call in calls)
    cost_per_query = (
        input_tokens * input_price_per_m
        + output_tokens * output_price_per_m
    ) / 1_000_000

    return CostEstimate(
        model=model,
        scenario=scenario,
        queries=queries,
        llm_calls_per_query=len(calls),
        input_tokens_per_query=input_tokens,
        output_tokens_per_query=output_tokens,
        input_price_per_m=input_price_per_m,
        output_price_per_m=output_price_per_m,
        estimated_cost_per_query_usd=cost_per_query,
        estimated_total_cost_usd=cost_per_query * queries,
        calls=calls,
    )


def render_markdown(estimate: CostEstimate) -> str:
    """Render a human-readable planning report."""
    rows = [
        "| Agent | Purpose | Input tokens | Output tokens |",
        "|---|---|---:|---:|",
    ]
    rows.extend(
        f"| {call.agent} | {call.purpose} | {call.input_tokens} | {call.output_tokens} |"
        for call in estimate.calls
    )
    return "\n".join(
        [
            "# Offline Cost Estimate",
            "",
            "> Planning estimate only. No provider API or billing endpoint was called.",
            "",
            f"- Model: `{estimate.model}`",
            f"- Scenario: `{estimate.scenario}`",
            f"- Queries: {estimate.queries}",
            f"- LLM calls/query: {estimate.llm_calls_per_query}",
            f"- Input tokens/query: {estimate.input_tokens_per_query:,}",
            f"- Output tokens/query: {estimate.output_tokens_per_query:,}",
            f"- Input price: ${estimate.input_price_per_m:.4f}/1M tokens",
            f"- Output price: ${estimate.output_price_per_m:.4f}/1M tokens",
            f"- Estimated cost/query: ${estimate.estimated_cost_per_query_usd:.6f}",
            f"- Estimated total: ${estimate.estimated_total_cost_usd:.6f}",
            "",
            *rows,
            "",
        ]
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario",
        choices=["auto", "legal", "tax", "compliance", "both"],
        default="both",
    )
    parser.add_argument("--question", default="")
    parser.add_argument("--queries", type=int, default=1)
    parser.add_argument("--question-tokens", type=int, default=40)
    parser.add_argument(
        "--model",
        default=os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL),
    )
    parser.add_argument(
        "--input-price",
        type=float,
        default=float(
            os.getenv(
                "OPENROUTER_INPUT_PRICE_PER_M",
                DEFAULT_INPUT_PRICE_PER_M,
            )
        ),
    )
    parser.add_argument(
        "--output-price",
        type=float,
        default=float(
            os.getenv(
                "OPENROUTER_OUTPUT_PRICE_PER_M",
                DEFAULT_OUTPUT_PRICE_PER_M,
            )
        ),
    )
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument(
        "--max-budget",
        type=float,
        help="Exit with an error when the estimated total exceeds this USD budget.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    scenario = (
        classify_scenario(args.question)
        if args.scenario == "auto"
        else args.scenario
    )
    estimate = estimate_cost(
        scenario=scenario,
        queries=args.queries,
        question_tokens=args.question_tokens,
        model=args.model,
        input_price_per_m=args.input_price,
        output_price_per_m=args.output_price,
    )
    markdown = render_markdown(estimate)
    print(markdown)

    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(asdict(estimate), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(markdown, encoding="utf-8")
    if (
        args.max_budget is not None
        and estimate.estimated_total_cost_usd > args.max_budget
    ):
        raise SystemExit(
            "Estimated cost "
            f"${estimate.estimated_total_cost_usd:.6f} exceeds "
            f"budget ${args.max_budget:.6f}"
        )


if __name__ == "__main__":
    main()
