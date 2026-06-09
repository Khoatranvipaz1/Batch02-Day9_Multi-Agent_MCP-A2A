"""End-to-end test client for the Legal Multi-Agent System.

Sends a legal question to the Customer Agent and prints the response.
"""

import asyncio
import os
import sys
from uuid import uuid4

import httpx
from dotenv import load_dotenv

from common.a2a_client import delegate

load_dotenv()

CUSTOMER_AGENT_URL = os.getenv("CUSTOMER_AGENT_URL", "http://localhost:10100")

QUESTION = (
    "If a company breaks a contract and avoids taxes, "
    "what are the legal and regulatory consequences?"
)


async def main() -> None:
    print(f"Connecting to Customer Agent at {CUSTOMER_AGENT_URL}")
    print(f"Question: {QUESTION}")
    print("-" * 60)

    async with httpx.AsyncClient(timeout=10.0) as http_client:
        # Resolve agent card
        card_url = f"{CUSTOMER_AGENT_URL}/.well-known/agent.json"
        try:
            card_resp = await http_client.get(card_url)
            card_resp.raise_for_status()
        except Exception as e:
            print(f"ERROR: Could not reach Customer Agent at {card_url}")
            print(f"  {e}")
            print("Make sure all services are running (./start_all.sh)")
            sys.exit(1)

        from a2a.types import AgentCard

        agent_card = AgentCard.model_validate(card_resp.json())
        print(f"Connected to agent: {agent_card.name} v{agent_card.version}")
        print("-" * 60)

        print("Sending request (the full agent chain may take a few minutes)...\n")
        context_id = str(uuid4())
        trace_id = str(uuid4())
        try:
            result_text = await delegate(
                endpoint=CUSTOMER_AGENT_URL,
                question=QUESTION,
                context_id=context_id,
                trace_id=trace_id,
                depth=0,
            )
        except TimeoutError as exc:
            print(f"ERROR: {exc}")
            print("Inspect logs/customer_agent.err.log and the downstream agent logs.")
            sys.exit(1)

        if result_text:
            print("RESPONSE:")
            print("=" * 60)
            print(result_text)
            print("=" * 60)
        else:
            print("No text response received.")
            print("Inspect the files in logs/ for the failed agent.")


if __name__ == "__main__":
    asyncio.run(main())
