# Báo cáo cá nhân - Vũ Đức Kiên
## MSSV: 2A202600338
## Vai trò: Analyst - Benchmark Execution, Failure Clustering và 5 Whys

---

### Nhiệm vụ được phân công
Theo phân công của nhóm, phần việc của tôi thuộc **Giai đoạn 3 (60')**:
- chạy benchmark trên bộ golden dataset
- đọc kết quả trong `reports/summary.json` và `reports/benchmark_results.json`
- phân cụm lỗi (failure clustering)
- phân tích nguyên nhân gốc rễ bằng phương pháp 5 Whys

---

### Công việc đã thực hiện
1. Chạy benchmark sau khi nhóm hoàn tất dataset, vector DB, agent và eval engine để tạo ra:
   - `reports/summary.json`
   - `reports/benchmark_results.json`
2. Kiểm tra các chỉ số đầu ra quan trọng của benchmark như:
   - `avg_score`
   - `hit_rate`
   - `mrr`
   - `agreement_rate`
   - `conflict_rate`
   - `pass_rate`
   - `error_rate`
3. Đọc từng case trong `reports/benchmark_results.json`, xác định các case fail, case điểm thấp và case error.
4. Gom lỗi thành các cụm thực tế để phục vụ chẩn đoán hệ thống:
   - grounded abstention despite evidence
   - ingestion / chunk truncation
   - retriever miss or wrong document
   - provider rate limits / quota
5. Chọn 3 case tiêu biểu để phân tích theo 5 Whys và truy vết lỗi về đúng tầng hệ thống:
   - ingestion / chunking
   - retrieval
   - prompting / output control
   - quota / provider reliability
6. Hoàn thiện nội dung file `analysis/failure_analysis.md` bằng số liệu benchmark thật thay vì placeholder.

---

### Bằng chứng đối chiếu trong repo
- `analysis/failure_analysis.md` hiện đã có:
  - tổng quan benchmark
  - bảng phân cụm lỗi
  - 3 case 5 Whys
  - action plan / trạng thái cải tiến
- `reports/summary.json` chứa các metric tổng hợp được sử dụng trực tiếp trong báo cáo phân tích lỗi.
- `reports/benchmark_results.json` chứa dữ liệu từng case để xác định fail cluster và chọn các case tệ nhất.
- `check_lab.py` đã nhận diện đủ file report và metric cần thiết, cho thấy benchmark output đã được nối đúng với phần phân tích.

---

### Đóng góp kỹ thuật chính
- Chuyển dữ liệu benchmark thô thành insight có thể hành động cho nhóm.
- Không chỉ đếm số case fail, tôi phân loại lỗi theo bản chất hệ thống để nhóm biết nên sửa ở ingestion, retrieval hay prompting.
- Áp dụng 5 Whys để đi từ triệu chứng bề mặt đến root cause có thể sửa được trong codebase.
- Biến `analysis/failure_analysis.md` từ template thành báo cáo thật phục vụ nộp bài.

---

### Kết quả đầu ra của phần việc
- Có báo cáo failure analysis hoàn chỉnh bám theo benchmark thực tế.
- Các root cause chính đã được chỉ ra đủ rõ để nhóm tiếp tục tối ưu agent ở giai đoạn 4.
- Báo cáo nhóm không còn placeholder như `X/Y`, `0.XX`, hay `[Mô tả ngắn]`.

---

### Kinh nghiệm rút ra
1. Một benchmark chỉ có giá trị khi có bước phân tích lỗi sau đó; nếu không thì các metric chỉ dừng ở mức mô tả.
2. Cần nhìn lỗi ở cấp hệ thống, không chỉ ở cấp câu trả lời sai.
3. 5 Whys giúp phân biệt rõ lỗi do dữ liệu, retrieval, prompting hay hạ tầng provider.
