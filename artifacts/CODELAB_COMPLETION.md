# Day 9 Codelab Completion

Status meanings:

- **Implemented**: code is present and passes compile/offline checks.
- **Verified live**: executed with the configured OpenRouter model.
- **Verified offline**: deterministic mock test; no provider API call.
- **Not run live**: implementation exists, but no live execution evidence was saved.

| Requirement | Status | Evidence |
|---|---|---|
| Stage 1 direct LLM | Verified live | 8.04 seconds |
| Stage 1 custom question | Verified live | Vietnamese labor-law question |
| Stage 1 temperature 0.3 | Verified live | `OPENROUTER_TEMPERATURE=0.3` |
| Stage 2 demo | Verified live | Tool call observed; 6.68 seconds |
| Stage 2 labor-law knowledge | Verified offline | `exercises/exercise_2_tools.py` |
| Stage 2 statute-of-limitations tool | Verified live | Exercise 2; 6.42 seconds |
| Stage 3 ReAct agent | Verified live | Three tool calls; 9.90 seconds |
| Stage 3 case-law tool | Implemented, verified offline | `search_case_law` |
| Stage 3 debugging | Verified live | `debug=True` and streamed updates |
| Stage 4 demo | Verified live | Parallel specialists; 13.17 seconds |
| Stage 4 graph diagram | Complete | `artifacts/stage4_graph.md` |
| Stage 4 Privacy Agent | Verified live | Exercise 4; 10.80 seconds |
| Stage 4 conditional routing | Verified live and offline | Tax and Privacy branches selected |
| Stage 5 distributed A2A | Verified live | Five local HTTP services |
| Dynamic discovery | Verified live | Registry discovered Law, Tax, Compliance |
| Parallel specialists | Verified live and offline | LangGraph `Send`; overlapping calls |
| Trace propagation | Verified live | E2E logs and sequence diagram |
| Delegation depth guard | Verified offline | `MAX_DELEGATION_DEPTH = 3` |
| Tax unavailable fallback | Verified live and offline | Tax stopped; response returned in 20.51 seconds |
| Modified Tax behavior | Verified live | Response limited to 300 words |
| E2E test | Verified live | Successful response returned |
| Offline evaluation | Verified offline | 6/6 checks passed |
| Cost planning | Verified offline | Estimator and budget gate |

## Remaining required checks

None. All five stages, both individual exercises, normal distributed E2E, and
the live Tax Agent outage procedure have been executed successfully.

## Optional advanced challenges

Persistent memory, authentication, exponential-backoff retry, and external
LangSmith/Prometheus monitoring are self-study challenges, not required for
the two-hour codelab.
