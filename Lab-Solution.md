# Day 9 Lab Solution

Tài liệu này tổng hợp lời giải các bài lab trên lớp và trỏ đến code đã chạy
trong repository.

## 1. Direct LLM Calling

### Bài 1.1 - Thay đổi câu hỏi

`stages/stage_1_direct_llm/main.py` dùng câu hỏi tiếng Việt về luật lao động.
Message gồm:

- `SystemMessage`: định nghĩa vai trò và nguyên tắc trả lời.
- `HumanMessage`: chứa câu hỏi của người dùng.

### Bài 1.2 - Temperature control

`common/llm.py` đọc `OPENROUTER_TEMPERATURE` từ `.env`, mặc định `0.3`.
Temperature thấp giúp kết quả ổn định hơn cho bài toán pháp lý.

## 2. LLM + RAG và Tools

### Bài 2.1 - Knowledge base luật lao động

`exercises/exercise_2_tools.py` đã thêm entry `labor_law` với từ khóa tiếng
Việt và tiếng Anh.

### Bài 2.2 - Tool thời hiệu

Đã implement:

```python
@tool
def check_statute_of_limitations(case_type: str) -> str:
    ...
```

Tool được đăng ký trong danh sách tools, dispatch qua `tool_map` và kết quả
được trả lại LLM bằng `ToolMessage`.

Chạy:

```powershell
uv run python exercises/exercise_2_tools.py
```

## 3. Single Agent ReAct

### Bài 3.1 - Tool án lệ

`stages/stage_3_single_agent/main.py` có tool `search_case_law`, hỗ trợ tra cứu
án lệ về breach, negligence và contract.

### Bài 3.2 - Debug reasoning

Graph được tạo với `debug=True` và chạy bằng `astream(...,
stream_mode="updates")` để quan sát từng tool call và observation.

## 4. Multi-Agent In-Process

### Bài 4.1 - Privacy Agent

`exercises/exercise_4_multiagent.py` đã bổ sung:

- `privacy_analysis` trong shared state.
- Node `privacy_agent`.
- Prompt chuyên GDPR và bảo vệ dữ liệu.
- Kết quả Privacy trong bước aggregate.

### Bài 4.2 - Conditional routing

Routing chọn Tax, Compliance và Privacy theo domain keywords. Các specialist
được dispatch song song bằng LangGraph `Send`.

Graph được mô tả tại `artifacts/stage4_graph.md`.

## 5. Distributed A2A

### Bài 5.1 - Trace request flow

Một `trace_id`, `context_id` và `delegation_depth` được truyền qua:

```text
Customer (depth 0)
  -> Law (depth 1)
       -> Tax + Compliance (depth 2, parallel)
```

Sequence diagram: `artifacts/stage5_sequence_diagram.md`.

### Bài 5.2 - Dynamic discovery và failure

Agents đăng ký với Registry và caller dùng `/discover/{task}` thay vì hardcode
agent selection. Khi Tax Agent bị dừng, Compliance vẫn hoàn thành và Law trả
về partial response. Live outage test hoàn thành trong `20.51s`.

### Bài 5.3 - Sửa Tax Agent

`tax_agent/graph.py` yêu cầu câu trả lời ngắn gọn dưới 300 từ. Service đã được
restart và kiểm tra live.

## 6. Bonus Latency

Baseline Stage 5: **20.11s**.

Giải pháp đã áp dụng:

1. Customer chuyển tiếp trực tiếp sang Law, bỏ hai LLM calls của ReAct gateway.
2. Law dùng deterministic keyword routing, bỏ một routing LLM call.
3. Tax và Compliance tiếp tục chạy song song.

Kết quả:

| Metric | Trước | Sau | Cải thiện |
|---|---:|---:|---:|
| Latency | 20.11s | 15.60s | 4.51s (22.4%) |
| LLM calls | 7 | 4 | Giảm 3 calls |
| Cost ước tính/query | $0.001200 | $0.000886 | Giảm 26.2% |

Chi tiết: `artifacts/LATENCY_OPTIMIZATION_REPORT.md`.

## 7. Assignment - Improve Day 8

Folder `Lab_Assignment/` cải tiến RAG Agent Day 8 bằng pattern
**Supervisor-Workers**:

- Supervisor phân công retrieval.
- Semantic Worker tìm theo độ tương đồng nội dung.
- Lexical Worker tìm bằng BM25.
- Citation Worker fusion, rerank và tạo câu trả lời có nguồn.

Hai retrieval workers chạy song song. Toàn bộ code, corpus mẫu, test và hướng
dẫn chạy đều nằm trong `Lab_Assignment/`.

## 8. Verification

Không gọi API:

```powershell
.\run_offline_checks.ps1
.\.venv\Scripts\python.exe -m unittest Lab_Assignment.test_supervisor -v
```

Live Stage 5 đã được kiểm tra với model
`google/gemini-2.5-flash-lite`.
