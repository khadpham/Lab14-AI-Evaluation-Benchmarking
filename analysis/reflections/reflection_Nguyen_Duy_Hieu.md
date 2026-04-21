# Báo cáo cá nhân - Nguyễn Duy Hiếu
## MSSV: 2A202600153
## Vai trò: Engineer - Agent Optimization và Final Submission

---

### Nhiệm vụ được phân công
Theo phân công của nhóm, phần việc của tôi thuộc **Giai đoạn 4 (45')**:
- tối ưu agent dựa trên kết quả benchmark và failure analysis
- hoàn thiện báo cáo nộp bài
- kiểm tra tính nhất quán giữa code, report và checklist trước khi nộp

---

### Công việc đã thực hiện
1. Đọc kết quả benchmark và báo cáo `analysis/failure_analysis.md` để xác định các vấn đề ưu tiên cần sửa trong agent.
2. Phối hợp tối ưu pipeline agent theo các hướng chính đã được chỉ ra bởi benchmark:
   - giảm lỗi retrieve sai section/chunk
   - giảm grounded abstention khi evidence có sẵn
   - làm sạch đầu ra để tránh lộ block `<think>`
3. Hỗ trợ tích hợp các cải tiến vào phiên bản agent hiện tại để kết quả benchmark sau sửa có thể phản ánh đúng chất lượng hệ thống.
4. Rà soát lại bộ hồ sơ nộp bài:
   - `reports/summary.json`
   - `reports/benchmark_results.json`
   - `analysis/failure_analysis.md`
   - các file reflection cá nhân
5. Kiểm tra định dạng trước khi nộp bằng `python check_lab.py` để bảo đảm repo đủ điều kiện chấm tự động.
6. Đồng bộ phần báo cáo với phần code đã có trong repo để tránh tình trạng code và report mô tả lệch nhau.

---

### Bằng chứng đối chiếu trong repo
- `analysis/failure_analysis.md` đã phản ánh trực tiếp các vấn đề cần tối ưu ở ingestion, retrieval, prompting và quota handling.
- `agent/main_agent.py` và `agent/helpers.py` là khu vực trọng tâm của phần tối ưu agent sau benchmark.
- `check_lab.py` đã pass, cho thấy phần final packaging và checklist nộp bài đã được hoàn thiện ở mức chạy được.
- Thư mục `analysis/reflections/` hiện đã có các báo cáo cá nhân tương ứng để hoàn tất submission checklist.

---

### Đóng góp kỹ thuật chính
- Biến kết quả benchmark thành hành động tối ưu cụ thể cho agent.
- Đảm bảo bài nộp không chỉ có code chạy được mà còn có báo cáo và hồ sơ đầy đủ, nhất quán.
- Đóng vai trò chốt cuối về mặt packaging: file đầu ra, report, reflection và kiểm tra định dạng.

---

### Kết quả đầu ra của phần việc
- Agent đã được xem xét và tối ưu theo đúng các lỗi quan trọng phát hiện từ benchmark.
- Hồ sơ nộp bài đã được hoàn thiện theo checklist:
  - source code
  - summary report
  - benchmark results
  - failure analysis
  - individual reflections
- Bài lab đã qua bước validate bằng `check_lab.py`.

---

### Kinh nghiệm rút ra
1. Tối ưu agent hiệu quả nhất khi bám trực tiếp vào failure analysis thay vì sửa cảm tính.
2. Một bài nộp mạnh cần cả hai phần: hệ thống chạy được và báo cáo giải thích được.
3. Bước validate cuối cùng rất quan trọng để tránh mất điểm do lỗi thủ tục hoặc thiếu file.
