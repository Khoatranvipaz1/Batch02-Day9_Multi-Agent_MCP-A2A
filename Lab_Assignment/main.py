"""CLI demo for the Day 8 Supervisor-Workers improvement."""

from __future__ import annotations

import argparse
import asyncio

from Lab_Assignment.supervisor import answer_question
from common.console import configure_utf8_console


DEFAULT_QUESTION = "Luật phòng chống ma túy quy định trách nhiệm của gia đình thế nào?"


async def main(question: str) -> None:
    result = await answer_question(question)
    print(f"Supervisor plan: {', '.join(result['plan'])}")
    print(f"Evidence count: {len(result['evidence'])}")
    print("-" * 60)
    print(result["answer"])


if __name__ == "__main__":
    configure_utf8_console()
    parser = argparse.ArgumentParser()
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    args = parser.parse_args()
    asyncio.run(main(args.question))
