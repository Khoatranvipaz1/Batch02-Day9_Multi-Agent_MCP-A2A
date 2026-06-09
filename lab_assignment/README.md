# Improve Day 8 Agent with Supervisor-Workers

## Mục tiêu

Cải tiến RAG Agent Day 8 thành kiến trúc Supervisor-Workers, giữ hybrid
retrieval và citation nhưng tách rõ trách nhiệm.

## Kiến trúc

```text
Question
   |
Supervisor
   |----------------------|
   v                      v
Semantic Worker      Lexical Worker
   |                      |
   +------ parallel ------+
              |
              v
       Citation Worker
              |
       Answer + sources
```

Workers:

1. `semantic_worker`: cosine similarity trên token-frequency vectors.
2. `lexical_worker`: BM25 retrieval.
3. `citation_worker`: RRF fusion, local reranking và grounded answer.

Supervisor dispatch hai retrieval workers bằng LangGraph `Send`; Citation
Worker chỉ chạy sau khi cả hai branch hoàn thành.

## Điểm cải tiến so với Day 8

- Tách retrieval/generation thành workers có ownership rõ.
- Semantic và Lexical retrieval chạy song song.
- Có thể thay từng worker bằng Weaviate, embedding model hoặc LLM khác mà không
  sửa orchestration.
- Citation Worker chỉ dùng evidence do retrieval cung cấp.
- Chạy offline, không cần API key; dễ test và tránh tốn quota.

## Chạy demo

Từ root Day 9:

```powershell
.\.venv\Scripts\python.exe -m lab_assignment.main
```

Đặt câu hỏi khác:

```powershell
.\.venv\Scripts\python.exe -m lab_assignment.main "Tàng trữ ma túy bị xử lý thế nào?"
```

## Chạy test

```powershell
.\.venv\Scripts\python.exe -m unittest lab_assignment.test_supervisor -v
```

Tests không gọi OpenRouter và kiểm tra:

- Supervisor tạo đúng plan.
- Semantic/Lexical workers chạy chồng lấp.
- Worker output đúng contract.
- Citation và abstention hoạt động.
