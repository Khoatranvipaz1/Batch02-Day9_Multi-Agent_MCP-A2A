"""Offline multi-agent evaluation using deterministic mocks.

No OpenRouter or external model endpoint is contacted.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Awaitable, Callable

import common.a2a_client as a2a_client
import common.registry_client as registry_client
import customer_agent.graph as customer_graph
import law_agent.graph as law_graph
from evals.cost_estimator import estimate_cost


@dataclass(frozen=True)
class EvalResult:
    name: str
    passed: bool
    duration_ms: float
    details: str


class ScriptedLLM:
    """Return deterministic responses based on the active system prompt."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def ainvoke(self, messages: list) -> SimpleNamespace:
        system = str(messages[0].content)
        self.calls.append(system)
        if "synthesising specialist analyses" in system:
            content = str(messages[-1].content)
            return SimpleNamespace(content=f"AGGREGATED\n{content}")
        return SimpleNamespace(content="LAW ANALYSIS")


async def _run_case(
    name: str,
    case: Callable[[], Awaitable[str]],
) -> EvalResult:
    started = time.perf_counter()
    try:
        details = await case()
        passed = True
    except Exception as exc:
        details = f"{type(exc).__name__}: {exc}"
        passed = False
    duration_ms = (time.perf_counter() - started) * 1000
    return EvalResult(name, passed, duration_ms, details)


def _base_state(depth: int = 1) -> dict:
    return {
        "question": "Contract breach with tax fraud and SEC compliance issues",
        "context_id": "context-eval",
        "trace_id": "trace-eval",
        "delegation_depth": depth,
        "law_analysis": "",
        "needs_tax": False,
        "needs_compliance": False,
        "tax_result": "",
        "compliance_result": "",
        "final_answer": "",
    }


async def eval_routing_matrix() -> str:
    cases = [
        ("A company breached a supply contract", []),
        ("The company committed tax evasion", ["call_tax"]),
        ("The SEC opened a regulatory investigation", ["call_compliance"]),
        (
            "IRS tax penalties and AML compliance failures",
            ["call_compliance", "call_tax"],
        ),
    ]
    for question, expected in cases:
        state = _base_state()
        state["question"] = question
        update = await law_graph.check_routing(state)
        state.update(update)
        destinations = sorted(
            send.node
            for send in law_graph.route_to_subagents(state)
            if send.node != "aggregate"
        )
        assert destinations == expected, (question, destinations, expected)
    return f"{len(cases)} deterministic routing combinations passed"


async def eval_depth_guard() -> str:
    update = await law_graph.check_routing(
        _base_state(depth=law_graph.MAX_DELEGATION_DEPTH)
    )
    assert update == {"needs_tax": False, "needs_compliance": False}
    return "max depth skipped specialist delegation"


async def eval_parallel_trace_and_aggregation() -> str:
    original_get_llm = law_graph.get_llm
    original_discover = registry_client.discover
    original_delegate = a2a_client.delegate
    llm = ScriptedLLM()
    active = 0
    max_active = 0
    both_started = asyncio.Event()
    calls: list[dict] = []

    async def fake_discover(task: str) -> str:
        return f"http://mock/{task}"

    async def fake_delegate(
        endpoint: str,
        question: str,
        context_id: str,
        trace_id: str,
        depth: int,
    ) -> str:
        nonlocal active, max_active
        calls.append(
            {
                "endpoint": endpoint,
                "context_id": context_id,
                "trace_id": trace_id,
                "depth": depth,
            }
        )
        active += 1
        max_active = max(max_active, active)
        if active == 2:
            both_started.set()
        await asyncio.wait_for(both_started.wait(), timeout=1.0)
        await asyncio.sleep(0.02)
        active -= 1
        return "TAX RESULT" if "tax_question" in endpoint else "COMPLIANCE RESULT"

    try:
        law_graph.get_llm = lambda: llm
        registry_client.discover = fake_discover
        a2a_client.delegate = fake_delegate
        result = await law_graph.create_graph().ainvoke(_base_state())

        assert max_active == 2, f"expected parallel overlap, got {max_active}"
        assert result["tax_result"] == "TAX RESULT"
        assert result["compliance_result"] == "COMPLIANCE RESULT"
        assert "TAX RESULT" in result["final_answer"]
        assert "COMPLIANCE RESULT" in result["final_answer"]
        assert len(calls) == 2
        assert all(call["context_id"] == "context-eval" for call in calls)
        assert all(call["trace_id"] == "trace-eval" for call in calls)
        assert all(call["depth"] == 2 for call in calls)
        return "parallel overlap=2; trace/context/depth propagated; aggregation passed"
    finally:
        law_graph.get_llm = original_get_llm
        registry_client.discover = original_discover
        a2a_client.delegate = original_delegate


async def eval_customer_delegation_tool() -> str:
    original_discover = registry_client.discover
    original_delegate = a2a_client.delegate
    captured: dict = {}

    async def fake_discover(task: str) -> str:
        assert task == "legal_question"
        return "http://mock/legal"

    async def fake_delegate(
        endpoint: str,
        question: str,
        context_id: str,
        trace_id: str,
        depth: int,
    ) -> str:
        captured.update(
            {
                "endpoint": endpoint,
                "question": question,
                "context_id": context_id,
                "trace_id": trace_id,
                "depth": depth,
            }
        )
        return "LAW NETWORK RESULT"

    try:
        registry_client.discover = fake_discover
        a2a_client.delegate = fake_delegate
        delegate_tool = customer_graph.create_delegate_tool(
            trace_id="trace-customer",
            context_id="context-customer",
            depth=0,
        )
        result = await delegate_tool.ainvoke({"question": "Legal question"})

        assert result == "LAW NETWORK RESULT"
        assert captured == {
            "endpoint": "http://mock/legal",
            "question": "Legal question",
            "context_id": "context-customer",
            "trace_id": "trace-customer",
            "depth": 1,
        }
        return "customer tool discovered Law Agent and propagated trace/context/depth"
    finally:
        registry_client.discover = original_discover
        a2a_client.delegate = original_delegate


async def eval_specialist_failure_fallback() -> str:
    original_get_llm = law_graph.get_llm
    original_discover = registry_client.discover
    original_delegate = a2a_client.delegate
    original_logger_disabled = law_graph.logger.disabled
    llm = ScriptedLLM()

    async def fake_discover(task: str) -> str:
        return f"http://mock/{task}"

    async def fake_delegate(
        endpoint: str,
        question: str,
        context_id: str,
        trace_id: str,
        depth: int,
    ) -> str:
        if "tax_question" in endpoint:
            raise RuntimeError("tax service unavailable")
        return "COMPLIANCE RESULT"

    try:
        law_graph.get_llm = lambda: llm
        law_graph.logger.disabled = True
        registry_client.discover = fake_discover
        a2a_client.delegate = fake_delegate
        result = await law_graph.create_graph().ainvoke(_base_state())

        assert "Tax analysis unavailable" in result["tax_result"]
        assert result["compliance_result"] == "COMPLIANCE RESULT"
        assert result["final_answer"].startswith("AGGREGATED")
        return "tax failure degraded gracefully; compliance and aggregation completed"
    finally:
        law_graph.get_llm = original_get_llm
        law_graph.logger.disabled = original_logger_disabled
        registry_client.discover = original_discover
        a2a_client.delegate = original_delegate


async def eval_cost_model() -> str:
    expected_calls = {
        "legal": 2,
        "tax": 3,
        "compliance": 3,
        "both": 4,
    }
    for scenario, call_count in expected_calls.items():
        estimate = estimate_cost(scenario=scenario, queries=10)
        assert estimate.llm_calls_per_query == call_count
        assert estimate.estimated_total_cost_usd > 0
    return "call counts and positive offline cost estimates passed for 4 scenarios"


def render_markdown(results: list[EvalResult]) -> str:
    passed = sum(result.passed for result in results)
    rows = [
        "| Eval | Status | Duration (ms) | Details |",
        "|---|---|---:|---|",
    ]
    rows.extend(
        "| {name} | {status} | {duration:.1f} | {details} |".format(
            name=result.name,
            status="PASS" if result.passed else "FAIL",
            duration=result.duration_ms,
            details=result.details.replace("|", "\\|"),
        )
        for result in results
    )
    return "\n".join(
        [
            "# Offline Multi-Agent Evaluation",
            "",
            "> No OpenRouter or external LLM API was called.",
            "",
            f"- Passed: {passed}/{len(results)}",
            f"- Score: {passed / len(results) * 100:.1f}%",
            "",
            *rows,
            "",
        ]
    )


async def run_all() -> list[EvalResult]:
    cases = [
        ("routing_matrix", eval_routing_matrix),
        ("depth_guard", eval_depth_guard),
        ("customer_delegation_tool", eval_customer_delegation_tool),
        ("parallel_trace_aggregation", eval_parallel_trace_and_aggregation),
        ("specialist_failure_fallback", eval_specialist_failure_fallback),
        ("cost_model", eval_cost_model),
    ]
    results = []
    for name, case in cases:
        results.append(await _run_case(name, case))
    return results


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("artifacts/offline_eval_report.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("artifacts/offline_eval_report.md"),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    results = asyncio.run(run_all())
    markdown = render_markdown(results)
    print(markdown)

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps([asdict(result) for result in results], indent=2),
        encoding="utf-8",
    )
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(markdown, encoding="utf-8")

    if not all(result.passed for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
