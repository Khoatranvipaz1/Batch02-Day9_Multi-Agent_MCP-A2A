# Offline Cost Estimate

> Planning estimate only. No provider API or billing endpoint was called.

- Model: `google/gemini-2.5-flash-lite`
- Scenario: `both`
- Queries: 100
- LLM calls/query: 4
- Input tokens/query: 2,860
- Output tokens/query: 1,500
- Input price: $0.1000/1M tokens
- Output price: $0.4000/1M tokens
- Estimated cost/query: $0.000886
- Estimated total: $0.088600

| Agent | Purpose | Input tokens | Output tokens |
|---|---|---:|---:|
| law | general legal analysis | 190 | 350 |
| tax | specialist tax analysis | 460 | 350 |
| compliance | specialist compliance analysis | 510 | 350 |
| law | aggregate legal and specialist analyses | 1700 | 450 |
