from agent.helpers import extract_answer_from_context, rerank_candidates, strip_think_block


def test_strip_think_block_returns_only_final_answer():
    raw = "<think>\ninternal reasoning\n</think>\n\nCisco AnyConnect được dùng cho VPN."

    assert strip_think_block(raw) == "Cisco AnyConnect được dùng cho VPN."


def test_rerank_candidates_prioritizes_matching_section():
    question = "Nhân viên sau probation period được làm remote tối đa mấy ngày một tuần?"
    candidates = [
        {
            "document": "12 ngày phép năm cho nhân viên dưới 3 năm kinh nghiệm.",
            "metadata": {
                "chunk_id": "hr_leave_policy_1.1_annual_leave",
                "section_title": "annual_leave",
                "doc_source": "hr/leave-policy-2026.pdf",
                "doc_id": "hr_leave_policy",
            },
            "distance": 0.11,
        },
        {
            "document": "Nhân viên sau probation period có thể làm remote tối đa 2 ngày/tuần.",
            "metadata": {
                "chunk_id": "hr_leave_policy_4_remote_work",
                "section_title": "remote_work",
                "doc_source": "hr/leave-policy-2026.pdf",
                "doc_id": "hr_leave_policy",
            },
            "distance": 0.19,
        },
        {
            "document": "Lead Engineer phân công engineer xử lý trong 10 phút.",
            "metadata": {
                "chunk_id": "sla_ticket_3_p1_process",
                "section_title": "p1_process",
                "doc_source": "support/sla-p1-2026.pdf",
                "doc_id": "sla_ticket",
            },
            "distance": 0.08,
        },
    ]

    ranked = rerank_candidates(question, candidates)

    assert ranked[0]["metadata"]["chunk_id"] == "hr_leave_policy_4_remote_work"


def test_extract_answer_from_context_uses_faq_question_answer_pair():
    question = "Tôi cần approval từ ai?"
    candidates = [
        {
            "document": (
                "Q: Tôi cần cài phần mềm mới, phải làm gì?\n"
                "A: Gửi yêu cầu qua Jira project IT-SOFTWARE. "
                "Line Manager phải phê duyệt trước khi IT cài đặt.\n\n"
                "Q: Ai chịu trách nhiệm gia hạn license phần mềm?\n"
                "A: IT Procurement team quản lý tất cả license."
            ),
            "metadata": {
                "chunk_id": "it_helpdesk_3_software_license",
                "section_title": "software_license",
                "doc_source": "support/helpdesk-faq.md",
                "doc_id": "it_helpdesk",
            },
            "distance": 0.12,
        }
    ]

    answer = extract_answer_from_context(question, candidates)

    assert answer == "Gửi yêu cầu qua Jira project IT-SOFTWARE. Line Manager phải phê duyệt trước khi IT cài đặt."
