"""CLI demo for the Day 8 Supervisor-Workers improvement."""

from __future__ import annotations

import argparse
import asyncio
import sys

from lab_assignment.supervisor import answer_question


DEFAULT_QUESTION = "Luật phòng chống ma túy quy định trách nhiệm của gia đình thế nào?"


async def main(question: str) -> None:
    result = await answer_question(question)
    print(f"Supervisor plan: {', '.join(result['plan'])}")
    print(f"Evidence count: {len(result['evidence'])}")
    print("-" * 60)
    print(result["answer"])


def configure_utf8_console() -> None:
    """Make Vietnamese CLI output reliable on Windows."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    configure_utf8_console()
    parser = argparse.ArgumentParser()
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    args = parser.parse_args()
    asyncio.run(main(args.question))
