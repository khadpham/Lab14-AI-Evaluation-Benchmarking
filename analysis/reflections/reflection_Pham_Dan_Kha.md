# Báo cáo cá nhân - Phạm Đan Kha
## MSSV: 2A202600253
## Vai trò: Data Engineer - Golden Dataset & SDG

---

### Nhiệm vụ được phân công
Theo phân công của nhóm và mô tả trong `README.md`, phần việc của tôi thuộc **Giai đoạn 1**, bao gồm:
- chuẩn bị dữ liệu nguồn và ingestion cho RAG
- tạo vector database phục vụ retrieval
- thiết kế Golden Dataset và Script SDG để sinh test cases đánh giá

---

### Công việc đã thực hiện
1. Xây dựng pipeline ingestion trong `data/ingest_docs.py` để đọc 5 tài liệu nguồn, tách section thành các chunk có `chunk_id` rõ ràng.
2. Tạo vector database bằng ChromaDB tại `data/vector_db/chroma_db/` để phục vụ retrieval cho hệ thống RAG.
3. Thiết kế và hoàn thiện script `data/synthetic_gen.py` để sinh bộ dữ liệu đánh giá ở định dạng JSONL.
4. Tạo file `data/golden_set.jsonl` gồm **100 test cases**, vượt yêu cầu tối thiểu 50 cases của đề bài.
5. Tổ chức test cases theo 5 nhóm rõ ràng, đúng với logic trong script:
   - `factual`: 25 cases
   - `paraphrase`: 20 cases
   - `ambiguous`: 20 cases
   - `adversarial`: 15 cases
   - `multi_turn`: 20 cases
6. Gắn `ground_truth_doc_ids`, `ground_truth_chunk_ids` và metadata cho từng case để phục vụ đánh giá retrieval ở các giai đoạn sau.
7. Xây dựng test set dựa trên 5 nguồn tài liệu chính trong `data/docs/`:
   - `hr_leave_policy.txt`
   - `it_helpdesk_faq.txt`
   - `policy_refund_v4.txt`
   - `access_control_sop.txt`
   - `sla_p1_2026.txt`
8. Bổ sung các nhóm câu hỏi khó như ambiguous, out-of-context, adversarial và multi-turn để dataset không chỉ gồm câu hỏi factual đơn giản.

---

### Bằng chứng đối chiếu trong repo
- `README.md` quy định Giai đoạn 1 là thiết kế Golden Dataset và SDG, tạo ít nhất 50 test cases.
- `data/ingest_docs.py` là pipeline ingestion của Stage 1, có các bước parse tài liệu, tạo embedding, ingest vào ChromaDB và lưu chunk metadata.
- `data/vector_db/chroma_db/` đang tồn tại trong repo, cho thấy đã có bước build/persist vector DB.
- `data/synthetic_gen.py` hiện là file trung tâm cho Stage 1 và có phần mô tả đầu file nêu rõ mục tiêu sinh **100 Golden Test Cases**.
- `data/golden_set.jsonl` hiện có **100 dòng**, phù hợp với đầu ra của script.
- Phân bố trong `golden_set.jsonl` khớp với logic của script:
  - factual: 25
  - paraphrase: 20
  - ambiguous: 20
  - adversarial: 15
  - multi_turn: 20
- `.gitignore` đang ignore `data/golden_set.jsonl`, cho thấy đây là file sinh ra từ bước chạy SDG chứ không phải dữ liệu tĩnh cần commit sẵn.
- `data/HARD_CASES_GUIDE.md` cũng phù hợp với hướng tôi đã triển khai khi đưa các hard cases như prompt injection, goal hijacking, ambiguous và out-of-context vào bộ test.

---

### Đóng góp kỹ thuật chính
- Xây ingestion pipeline để chuyển tài liệu thô thành các chunk có cấu trúc, là nền cho cả vector DB lẫn bộ golden set.
- Tạo vector DB persist bằng ChromaDB để nhóm có thể dùng cho retrieval evaluation và RAG pipeline.
- Xây bộ dữ liệu có cấu trúc đủ để chấm cả **answer quality** lẫn **retrieval quality**, vì mỗi case đều gắn ground truth theo tài liệu/chunk.
- Không chỉ tạo câu hỏi trực tiếp, tôi còn bổ sung các trường hợp kiểm thử khó hơn để hỗ trợ nhóm đánh giá độ bền của agent:
  - câu hỏi diễn đạt lại
  - câu hỏi mơ hồ
  - câu hỏi ngoài phạm vi tài liệu
  - câu hỏi đối kháng/prompt injection
  - các lượt hỏi phụ thuộc ngữ cảnh trước đó
- Chuẩn hóa đầu ra theo JSONL để `main.py` có thể đọc trực tiếp khi chạy benchmark.

---

### Kết quả đầu ra của phần việc
- Hoàn thành phần ingestion/chunking và tạo vector DB phục vụ retrieval.
- Hoàn thành vượt yêu cầu tối thiểu về số lượng test case.
- Tạo được dataset đủ rộng để nhóm tiếp tục làm các phần:
  - retrieval metrics như Hit Rate, MRR
  - judge scoring / agreement rate
  - benchmark runner
  - failure analysis ở các giai đoạn sau
- Đây là phần nền cho toàn bộ pipeline đánh giá, vì các bước benchmark phía sau đều đọc từ `data/golden_set.jsonl`.

---

### Hạn chế và lưu ý
- `data/ingest_docs.py` có logic sinh `data/chunks_metadata.json`, nhưng trong workspace hiện tại file này chưa có mặt; vì vậy tôi chỉ nên khẳng định chắc phần ingestion/vector DB và cấu trúc `chunk_id`, không nên nói chắc rằng file metadata đã được giữ lại trong repo.
- Một số test case adversarial hoặc out-of-context có `ground_truth_doc_ids` rỗng; đây là chủ đích thiết kế để kiểm tra khả năng từ chối hoặc trả lời đúng phạm vi, không phải lỗi dữ liệu.
- Tôi chỉ nhận phần Stage 1, nên các nội dung về multi-judge, async runner, failure clustering hay tối ưu agent không thuộc phần đóng góp chính của tôi.

---

### Kinh nghiệm rút ra
1. Dataset tốt phải đo được đúng thứ cần đo. Nếu ground truth không rõ thì các chỉ số retrieval như Hit Rate hay MRR sẽ mất ý nghĩa.
2. Bộ test chỉ gồm câu hỏi dễ sẽ làm benchmark bị "đẹp giả". Các nhóm ambiguous, adversarial và out-of-context giúp kiểm tra agent thực tế hơn.
3. Việc chuẩn hóa schema ngay từ đầu giúp các thành viên ở giai đoạn sau tích hợp thuận lợi hơn và giảm lỗi khi chạy benchmark.
