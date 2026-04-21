# Báo cáo cá nhân - Trần Đặng Quang Huy
## MSSV: 2A202600292
## Vai trò: AI/Backend Engineer - Eval Engine, Multi-Judge và Async Runner

---

### Nhiệm vụ được phân công
Theo phân công của nhóm, phần việc của tôi thuộc **Giai đoạn 2 (90')**:
- phát triển Eval Engine
- triển khai Multi-Judge / Custom Judge
- xây Async Runner để benchmark chạy song song ổn định

---

### Công việc đã thực hiện
1. Nâng cấp `main.py` từ bản mock đơn giản sang pipeline benchmark có thống kê thực tế hơn:
   - khởi tạo `BenchmarkRunner`
   - dùng `RetrievalEvaluator`
   - dùng `LLMJudge`
   - tổng hợp các chỉ số như `avg_score`, `hit_rate`, `mrr`, `agreement_rate`, `conflict_rate`, `avg_latency_sec`, `pass_rate`, `error_rate`
2. Hoàn thiện `engine/retrieval_eval.py` để tính retrieval metrics theo từng case:
   - chuẩn hóa input id
   - tính `Hit Rate@k`
   - tính `MRR`
   - hỗ trợ tổng hợp theo batch
3. Hoàn thiện `engine/runner.py` theo hướng async thực dụng:
   - chạy đồng thời bằng `asyncio`
   - dùng `Semaphore` để giới hạn concurrency
   - bổ sung retry cho từng stage
   - tách trạng thái `pass`, `fail`, `error`
   - ghi lại lỗi theo từng test case
4. Xây `engine/llm_judge.py` theo hướng multi-judge:
   - dùng 2 judge model độc lập: Gemini và Groq/Qwen
   - ép model trả về JSON
   - chuẩn hóa rubric theo các tiêu chí `accuracy`, `professionalism`, `safety`
   - tính `agreement_rate`
   - phát hiện conflict điểm số
   - có logic hòa giải khi 2 model lệch nhiều
   - có fallback single-judge nếu một provider bị lỗi
5. Viết lại `agent/main_agent.py` thành baseline Dense Retrieval Agent:
   - load ChromaDB persistent
   - embed câu hỏi bằng `SentenceTransformer`
   - truy vấn vector DB
   - chọn top-k context
   - gọi Groq để sinh grounded answer
   - trả về `retrieved_ids`, `contexts`, `sources` và metadata phục vụ benchmark

---

### Bằng chứng đối chiếu trong repo
- `main.py` hiện import trực tiếp:
  - `BenchmarkRunner`
  - `RetrievalEvaluator`
  - `LLMJudge`
  - `MainAgent`
- `engine/runner.py` có:
  - `max_concurrency`
  - `max_retries`
  - `retry_backoff_seconds`
  - semaphore để giới hạn đồng thời
  - retry riêng cho `agent.query`, `evaluator.score`, `judge.evaluate_multi_judge`
- `engine/retrieval_eval.py` có đầy đủ logic:
  - `_normalize_ids`
  - `evaluate_case`
  - `calculate_hit_rate`
  - `calculate_mrr`
- `engine/llm_judge.py` dùng:
  - `google.genai`
  - `AsyncOpenAI` với `base_url="https://api.groq.com/openai/v1"`
  - 2 hàm `_judge_with_gemini` và `_judge_with_groq`
  - logic `_compute_agreement` và `_resolve_conflict`
- `agent/main_agent.py` đã kết nối thực tới:
  - `data/vector_db/chroma_db`
  - collection `evaluation_docs`
  - embedding model
  - Groq model để answer generation

---

### Đóng góp kỹ thuật chính
- Biến phần benchmark từ bản placeholder thành một pipeline có thể đo retrieval, judge consensus và khả năng chạy async.
- Tạo kiến trúc đủ gần bài toán thật:
  - retrieval riêng
  - generation riêng
  - evaluation riêng
  - judge consensus riêng
- Bổ sung khả năng chịu lỗi tốt hơn bằng retry, concurrency limit và fallback khi một judge provider gặp lỗi.
- Định hình chuẩn đầu ra cho `reports/summary.json` và `reports/benchmark_results.json` để nhóm có thể dùng cho phân tích giai đoạn sau.

---

### Kết quả đầu ra của phần việc
- Có baseline agent truy vấn trực tiếp từ vector DB thay vì agent giả lập hoàn toàn.
- Có retrieval metrics để nối đúng với Golden Dataset của giai đoạn 1.
- Có multi-judge consensus engine dùng 2 nguồn chấm độc lập.
- Có async runner để chuẩn bị cho việc benchmark trên toàn bộ dataset 100 cases.

---

### Hạn chế và lưu ý khi chạy
- Code hiện yêu cầu API key thật cho:
  - `GROQ_API_KEY`
  - `GEMINI_API_KEY` hoặc `GOOGLE_API_KEY`
- `.env.example` hiện **chưa đồng bộ hoàn toàn** với code:
  - code dùng `VECTOR_COLLECTION` nhưng file mẫu ghi `CHROMA_COLLECTION_NAME`
  - code dùng `BASELINE_AGENT_MODEL` nhưng file mẫu ghi `AGENT_LLM_MODEL`
  - code dùng `LLM_JUDGE_GEMINI_MODEL` và `LLM_JUDGE_GROQ_MODEL` nhưng file mẫu lại ghi `JUDGE_MODELS`
- Vì vậy khi chạy thực tế cần sửa `.env` theo tên biến mà code đang đọc, không chỉ copy nguyên `.env.example`.

---

### Kinh nghiệm rút ra
1. Multi-judge chỉ có ý nghĩa khi có chuẩn hóa output và cơ chế xử lý conflict rõ ràng.
2. Async benchmark không chỉ là `gather`, mà còn cần semaphore, retry và phân loại lỗi theo case để pipeline không gãy toàn bộ.
3. Việc đồng bộ tên biến môi trường giữa code và `.env.example` rất quan trọng; lệch naming sẽ làm hệ thống không chạy được dù code logic đã đúng.
