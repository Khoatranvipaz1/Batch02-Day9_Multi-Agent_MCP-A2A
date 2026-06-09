"""Customer Agent delegation tool.

The Customer Agent uses `delegate_to_legal_agent` directly so the request:
1. Discovers the Law Agent via the registry
2. Sends the question to it via A2A
3. Returns the comprehensive legal response to the user

The tool accepts context propagation data (trace_id, context_id, depth)
via a closure — these are bound per-request in agent_executor.py.
"""

from __future__ import annotations

import logging

from langchain_core.tools import BaseTool, tool

logger = logging.getLogger(__name__)


def create_delegate_tool(
    trace_id: str,
    context_id: str,
    depth: int,
) -> BaseTool:
    """Create the legal delegation tool with request trace context."""

    @tool("delegate_to_legal_agent")
    async def delegate_to_legal_agent(question: str) -> str:
        """Send a legal question to the Law Agent for comprehensive analysis.

        The Law Agent will coordinate Tax and Compliance sub-agents in parallel
        and return a synthesised response covering all relevant legal dimensions.

        Args:
            question: The legal question to analyse.

        Returns:
            A comprehensive legal analysis from the multi-agent system.
        """
        from common.a2a_client import delegate
        from common.registry_client import discover

        logger.info(
            "Customer delegate_to_legal_agent | trace=%s context=%s depth=%d",
            trace_id, context_id, depth,
        )

        try:
            endpoint = await discover("legal_question")
            result = await delegate(
                endpoint=endpoint,
                question=question,
                context_id=context_id,
                trace_id=trace_id,
                depth=depth + 1,
            )
            if not result:
                return "The Law Agent returned an empty response. Please try again."
            return result
        except Exception as exc:
            logger.exception("delegate_to_legal_agent failed: %s", exc)
            return f"Could not reach the Law Agent: {exc}"

    return delegate_to_legal_agent
