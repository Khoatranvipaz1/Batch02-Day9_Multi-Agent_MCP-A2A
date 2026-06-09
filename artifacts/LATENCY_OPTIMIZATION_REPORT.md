# Multi-Agent Latency and Optimization Report

## Measurement

Source: the successful distributed Stage 5 trace
`84c679b7-4fbd-40cd-90b2-364279b54228` recorded on June 9, 2026.
The client measured the complete request at **20.11 seconds**.

| Component | Observed time | How it was derived |
|---|---:|---|
| Customer Agent server work | about 17.33s | Execute at 15:14:19.926 through its final LLM response at 15:14:37.256 |
| Law Agent delegation | 12.18s | A2A delegation at 15:14:24.224 through completion at 15:14:36.404 |
| Tax Agent | 3.64s | Execute at 15:14:29.551 through HTTP response at 15:14:33.186 |
| Compliance Agent | 3.30s | Execute at 15:14:29.786 through HTTP response at 15:14:33.083 |
| Tax + Compliance critical path | 3.64s | Both branches overlap; the slower branch determines latency |
| Client and A2A overhead outside Customer work | about 2.78s | 20.11s total minus about 17.33s server work |

Times are reconstructed from millisecond log timestamps, so values other than
the client total are approximate. New instrumentation now logs monotonic
`duration_ms` for every agent execution and A2A delegation.

## Interpretation

The four agent durations must not be added together. Customer contains Law,
and Law contains the parallel Tax and Compliance calls. The request's critical
path is approximately:

```text
client/A2A -> Customer pre-processing -> Law analysis and routing
           -> max(Tax, Compliance) -> Law aggregation
           -> Customer final formatting -> client
```

Parallel specialist dispatch is already effective. Sequential LLM turns in
Customer and Law are the main latency source. Registry discovery and fetching
an Agent Card for every delegation add smaller network overhead.

## Recommended Improvements

| Priority | Improvement | Expected effect | Trade-off |
|---|---|---|---|
| P0 | Keep Tax and Compliance parallel | Saves about 3.30s versus sequential execution in this trace | Already implemented |
| P1 | Remove Customer's final LLM rewrite and return the Law result directly | Removes one sequential LLM call, likely saving roughly 1-3s and output tokens | Customer cannot reformat the answer |
| P1 | Combine Law analysis and routing into one structured-output LLM call | Removes one sequential LLM call, likely saving roughly 1-3s | Prompt/schema requires careful validation |
| P1 | Cache registry discovery and Agent Cards with a short TTL | Avoids repeated local HTTP lookups on warm requests; likely saves sub-second to about 2s across the chain | Must expire cache when endpoints change |
| P2 | Use deterministic keyword routing before LLM fallback | Eliminates routing LLM latency for clear tax/compliance questions | Ambiguous questions still need LLM routing |
| P2 | Reduce prompt and response limits | Improves generation time and cost | Responses become less detailed |
| P2 | Stream the final response | Improves time-to-first-token, though total completion time changes little | Requires streaming support through the A2A/UI path |
| P3 | Add repeated benchmark runs and report median/P95 | Produces reliable performance evidence | Live runs consume API quota |

## Practical Target

The current measured baseline is **20.11s**. Removing the Customer rewrite and
one Law routing call should remove two sequential LLM calls. A conservative
target for the same workload is **14-17s** end to end. Caching discovery/card
metadata can improve warm requests further. This is an estimate and must be
verified with at least 5 live runs; report median and P95 rather than one run.

## Benchmark Procedure

1. Start all five services and let one warm-up request finish.
2. Run the same question at least five times.
3. Record client elapsed time and each log line containing `duration_ms`.
4. Calculate median, minimum, maximum, and P95.
5. Compare with the 20.11s baseline using the same model and token limits.

No additional OpenRouter request was made to produce this report.
