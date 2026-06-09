"""Offline tests for the Day 8 Supervisor-Workers assignment."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

import Lab_Assignment.supervisor as supervisor
from Lab_Assignment.workers import citation_worker, lexical_worker, semantic_worker


class SupervisorWorkersTest(unittest.IsolatedAsyncioTestCase):
    async def test_supervisor_dispatches_three_worker_pipeline(self) -> None:
        result = await supervisor.answer_question(
            "Luật phòng chống ma túy quy định trách nhiệm gia đình thế nào?"
        )
        self.assertEqual(
            result["plan"],
            ["semantic_worker", "lexical_worker"],
        )
        self.assertTrue(result["evidence"])
        self.assertIn("[", result["answer"])
        self.assertIn("Nguồn:", result["answer"])

    async def test_retrieval_workers_overlap(self) -> None:
        active = 0
        maximum_active = 0
        both_started = asyncio.Event()

        async def delayed_worker(state: dict) -> dict:
            nonlocal active, maximum_active
            active += 1
            maximum_active = max(maximum_active, active)
            if active == 2:
                both_started.set()
            await asyncio.wait_for(both_started.wait(), timeout=1)
            await asyncio.sleep(0.01)
            active -= 1
            return {"worker_results": [[]]}

        with (
            patch.object(supervisor, "run_semantic_worker", delayed_worker),
            patch.object(supervisor, "run_lexical_worker", delayed_worker),
        ):
            graph = supervisor.create_graph()
            await graph.ainvoke(
                {
                    "query": "test query",
                    "plan": [],
                    "worker_results": [],
                    "evidence": [],
                    "answer": "",
                }
            )
        self.assertEqual(maximum_active, 2)

    async def test_empty_query_abstains(self) -> None:
        result = await supervisor.answer_question("")
        self.assertEqual(result["plan"], [])
        self.assertIn("I cannot verify this information", result["answer"])


class WorkerTest(unittest.TestCase):
    def test_semantic_and_lexical_contract(self) -> None:
        for results in (
            semantic_worker("trách nhiệm gia đình"),
            lexical_worker("trách nhiệm gia đình"),
        ):
            self.assertTrue(results)
            self.assertIn("content", results[0])
            self.assertIn("score", results[0])
            self.assertIn("metadata", results[0])

    def test_citation_worker_abstains_without_evidence(self) -> None:
        answer = citation_worker("Thông tin không tồn tại", [])
        self.assertIn("I cannot verify this information", answer)


if __name__ == "__main__":
    unittest.main()
