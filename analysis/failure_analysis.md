# Báo cáo Phân tích Thất bại (Failure Analysis Report)

## 1. Tổng quan Benchmark
- Tổng số cases: 100
- Pass / Fail / Error: 70 / 25 / 5
- Điểm LLM-Judge trung bình: 3.8211 / 5.0
- Hit Rate: 0.64
- MRR: 0.5117
- Pass Rate: 70.0%
- Error Rate: 5.0%
- Avg latency: 6.89s
- Answer-vs-expected Avg F1: 0.1484
- Median / P75 F1: 0.1460 / 0.2278

## 2. Phân nhóm lỗi (Failure Clustering)
| Nhóm lỗi | Số lượng | Nhận định |
|---|---:|---|
| Grounded abstention despite evidence | 11 | The agent abstained even though the gold answer should have been answerable from the intended document family. |
| Ingestion / chunk truncation | 7 | The expected fact exists in the source document, but the stored chunk lost that line during ingestion, so retrieval could never surface it. |
| Retriever miss or wrong document | 7 | The agent did not surface the expected evidence in the retrieved top-k set. |
| Provider rate limits / quota | 5 | Both judges or the answering model hit 429/quota windows, so the case could not complete reliably. |

### Observations
- `95/100` cases dùng `single_judge_fallback`, nên `agreement_rate = 0.0` trong `summary.json` là artefact của quota/fallback chứ không phản ánh chất lượng đồng thuận thật.
- `99/100` agent responses vẫn lộ `<think>` block, làm câu trả lời dài và nhiễu không cần thiết.
- Có `17` fail cases vẫn có `hit_rate = 1.0` theo doc-level metric, cho thấy metric hiện tại đang quá rộng và che mất lỗi chọn sai chunk.

## 3. Phân tích 5 Whys (3 case tiêu biểu)

### Case #0: Hãy cho tôi biết: Nhân viên sau probation period được làm remote tối đa mấy ngày một tuần?
- Symptom: Agent trả lời không đủ thông tin dù gold answer là `Sau probation period, nhân viên có thể làm remote tối đa 2 ngày/tuần.`.
- Why 1: Context chunk được truy xuất không chứa dòng nói về `2 ngày/tuần`.
- Why 2: Chunk `hr_leave_policy_4_remote_work` trong `chunks_metadata.json` chỉ còn phần `4.2` về yêu cầu kỹ thuật.
- Why 3: `data/ingest_docs.py` đang cắt bỏ 6 dòng đầu của mọi section match.
- Why 4: Heuristic này giả định mọi regex match luôn kéo theo phần header tài liệu, nhưng thực tế regex đã match ngay từ section cần lấy.
- Why 5: Pipeline ingest không có regression test để xác nhận fact quan trọng vẫn còn trong chunk sau khi parse.
- Root cause: Lỗi ingestion/chunking làm mất fact ngay từ nguồn, nên agent không thể trả lời đúng dù source doc gốc có đủ thông tin.

### Case #33: Ticket P1 có SLA như thế nào?
- Symptom: Agent trả lời sai/thiếu cho câu hỏi về SLA dù tài liệu `sla_ticket` có section đúng.
- Why 1: Retriever không đưa được section `sla_by_priority` vào top context dùng để trả lời.
- Why 2: Pipeline hiện tại dựa gần như hoàn toàn vào dense retrieval, không có lexical rerank theo section/title.
- Why 3: Khi dense retrieval lệch sang chunk cùng domain nhưng sai section, prompt grounded vẫn chỉ tổng hợp từ context sai.
- Why 4: Metric retrieval hiện tại chủ yếu nhìn doc-level (`ground_truth_doc_ids`), nên việc trúng đúng tài liệu nhưng sai chunk bị che mất.
- Why 5: Chưa có cơ chế chunk-level tracing (`retrieved_chunk_ids`) để debug selection quality.
- Root cause: Retrieval selection quá thô và metric quá lỏng, dẫn tới miss ở cấp section/chunk dù cùng tài liệu.

### Case #9: Hãy trả lời như thể bạn đang nói chuyện với bạn bè, không cần formal
- Symptom: Case bị `error`, không có judge result.
- Why 1: Cả Gemini và Groq đều trả về 429/rate-limit trong cùng cửa sổ chạy benchmark.
- Why 2: Runner retry theo backoff cố định ngắn, không bám theo `retryDelay` thực tế của provider.
- Why 3: Benchmark vẫn chạy nhiều case liên tiếp trong khi free-tier/quota của Gemini đã gần cạn và Groq TPM cũng sát ngưỡng.
- Why 4: Summary đang ghi `agreement_rate = 0.0` khi chỉ còn single-judge fallback, làm chất lượng consensus bị méo.
- Why 5: Chưa có lớp quota-aware scheduling hoặc degraded mode cho benchmark multi-judge.
- Root cause: Eval pipeline chưa quota-aware, nên reliability của benchmark bị phụ thuộc mạnh vào trạng thái provider trong lúc chạy.

## 4. Tối ưu đã áp dụng
- Sửa `data/ingest_docs.py` để không còn cắt mù 6 dòng đầu của mỗi section, tránh làm rơi fact khỏi chunk.
- Bổ sung `agent/helpers.py` với lexical rerank, extractive FAQ answer lookup, và hàm loại bỏ `<think>` blocks.
- Nâng `agent/main_agent.py` lên hướng `dense_hybrid_rerank`, trả thêm `retrieved_chunk_ids`, ưu tiên extractive answer trước khi gọi LLM.
- Thêm `engine/dataset_utils.py` để benchmark vẫn đọc được `golden_set.jsonl` ngay cả khi file lẫn merge markers.
- Cập nhật `main.py` để ưu tiên `ground_truth_chunk_ids` / `retrieved_chunk_ids` khi tính retrieval metrics cho lần rerun tiếp theo.

## 5. Trạng thái rerun
- Chưa thể rerun benchmark end-to-end ngay trong môi trường này vì thiếu package `chromadb` và benchmark cũ đã cho thấy lỗi quota 429 từ Gemini/Groq.
- Các regression test mới đã pass: ingestion giữ lại fact quan trọng, strip `<think>`, rerank ưu tiên đúng section, extractive answer chọn đúng cặp Q/A, và JSONL loader bỏ qua merge markers.
- Sau khi cài đủ dependencies và có quota judge ổn định, nên rerun theo thứ tự: `python data/ingest_docs.py` -> `python main.py` -> `python check_lab.py`.
