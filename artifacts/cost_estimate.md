# Offline Cost Estimate

> Planning estimate only. No provider API or billing endpoint was called.

- Model: `google/gemini-2.5-flash-lite`
- Scenario: `both`
- Queries: 100
- LLM calls/query: 7
- Input tokens/query: 4,500
- Output tokens/query: 1,875
- Input price: $0.1000/1M tokens
- Output price: $0.4000/1M tokens
- Estimated cost/query: $0.001200
- Estimated total: $0.120000

| Agent | Purpose | Input tokens | Output tokens |
|---|---|---:|---:|
| customer | decide and call delegate_to_legal_agent | 470 | 50 |
| law | general legal analysis | 190 | 350 |
| law | route to specialist agents | 220 | 25 |
| tax | specialist tax analysis | 460 | 350 |
| compliance | specialist compliance analysis | 510 | 350 |
| law | aggregate legal and specialist analyses | 1700 | 450 |
| customer | present the delegated answer | 950 | 300 |
