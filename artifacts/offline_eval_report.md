# Offline Multi-Agent Evaluation

> No OpenRouter or external LLM API was called.

- Passed: 6/6
- Score: 100.0%

| Eval | Status | Duration (ms) | Details |
|---|---|---:|---|
| routing_matrix | PASS | 0.1 | 4 deterministic routing combinations passed |
| depth_guard | PASS | 0.0 | max depth skipped specialist delegation |
| customer_delegation_tool | PASS | 5.2 | customer tool discovered Law Agent and propagated trace/context/depth |
| parallel_trace_aggregation | PASS | 49.9 | parallel overlap=2; trace/context/depth propagated; aggregation passed |
| specialist_failure_fallback | PASS | 13.5 | tax failure degraded gracefully; compliance and aggregation completed |
| cost_model | PASS | 0.1 | call counts and positive offline cost estimates passed for 4 scenarios |
