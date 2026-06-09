"""LangGraph Supervisor-Workers orchestration for the Day 8 RAG agent."""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.constants import Send
from langgraph.graph import END, StateGraph

from Lab_Assignment.workers import (
    Evidence,
    citation_worker,
    lexical_worker,
    reciprocal_rank_fusion,
    semantic_worker,
)


class SupervisorState(TypedDict):
    query: str
    plan: list[str]
    worker_results: Annotated[list[list[Evidence]], operator.add]
    evidence: list[Evidence]
    answer: str


def supervisor_agent(state: SupervisorState) -> dict:
    """Create a deterministic plan for the hybrid Day 8 RAG request."""
    if not state["query"].strip():
        return {"plan": []}
    return {"plan": ["semantic_worker", "lexical_worker"]}


def dispatch_workers(state: SupervisorState) -> list[Send]:
    """Dispatch independent retrieval workers in parallel."""
    if not state["plan"]:
        return [Send("citation_worker", state)]
    return [
        Send(worker_name, {"query": state["query"]})
        for worker_name in state["plan"]
    ]


def run_semantic_worker(state: dict) -> dict:
    return {"worker_results": [semantic_worker(state["query"])]}


def run_lexical_worker(state: dict) -> dict:
    return {"worker_results": [lexical_worker(state["query"])]}


def run_citation_worker(state: SupervisorState) -> dict:
    evidence = reciprocal_rank_fusion(state.get("worker_results", []))
    return {
        "evidence": evidence[:5],
        "answer": citation_worker(state["query"], evidence),
    }


def create_graph():
    graph = StateGraph(SupervisorState)
    graph.add_node("supervisor", supervisor_agent)
    graph.add_node("semantic_worker", run_semantic_worker)
    graph.add_node("lexical_worker", run_lexical_worker)
    graph.add_node("citation_worker", run_citation_worker)

    graph.set_entry_point("supervisor")
    graph.add_conditional_edges(
        "supervisor",
        dispatch_workers,
        ["semantic_worker", "lexical_worker", "citation_worker"],
    )
    graph.add_edge(
        ["semantic_worker", "lexical_worker"],
        "citation_worker",
    )
    graph.add_edge("citation_worker", END)
    return graph.compile()


async def answer_question(query: str) -> dict:
    """Run the complete Supervisor-Workers graph."""
    return await create_graph().ainvoke(
        {
            "query": query,
            "plan": [],
            "worker_results": [],
            "evidence": [],
            "answer": "",
        }
    )
